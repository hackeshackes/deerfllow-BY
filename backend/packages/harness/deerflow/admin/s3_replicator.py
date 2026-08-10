"""AWS S3 object-store adapter implementing :class:`deerflow.admin.replication.SecretReplicator` (v1.7 M4).

This adapter talks to AWS S3's object surface (GET / PUT / HEAD) with a
hand-rolled AWS Signature V4 — no boto3. HTTP rides on ``httpx`` (a project
runtime dep); the signing math itself is standard library only.

Design notes:
* Transport-agnostic contract: ``get`` / ``put`` / ``exists`` mirror the
  ``SecretReplicator`` Protocol exactly, so the admin layer can swap S3 for
  GCS / Aliyun OSS later without touching the ``ReplicationManager``.
* ``readonly=True`` guards replica writes (useful for a DR/read-only region).
* ``client`` is injectable so tests use a ``httpx.MockTransport`` — no network.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from .replication import SecretReplicator

logger = logging.getLogger(__name__)

_SERVICE = "s3"
_ALGORITHM = "AWS4-HMAC-SHA256"


class S3Replicator(SecretReplicator):
    """Sign-and-forward S3 object API over ``httpx``."""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        session_token: str | None = None,
        readonly: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not endpoint:
            raise ValueError("endpoint is required")
        if not bucket:
            raise ValueError("bucket is required")
        if not region:
            raise ValueError("region is required")
        if not access_key or not secret_key:
            raise ValueError("access_key and secret_key are required")
        self.endpoint = endpoint.rstrip("/")
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.readonly = readonly
        self._client = client or httpx.AsyncClient()

    # -- signing -------------------------------------------------------------

    def sign(
        self,
        method: str,
        path: str,
        query: str,
        headers: dict[str, str],
        body: bytes,
        amz_date: str,
    ) -> str:
        """Return the 64-hex AWS Signature V4 authorization signature.

        Exposed as a small pure function so tests can assert determinism and
        an operator can verify a known AWS test vector without a live server.
        """
        credential_scope = f"{amz_date}/{self.region}/{_SERVICE}/aws4_request"

        canonical_headers = "".join(
            f"{k.lower()}:{headers[k].strip()}\n" for k in sorted(headers)
        )
        signed_headers = ";".join(k.lower() for k in sorted(headers))
        payload_hash = hashlib.sha256(body).hexdigest()

        canonical_request = "\n".join(
            [method.upper(), path, query, canonical_headers, signed_headers, payload_hash]
        )

        string_to_sign = "\n".join(
            [
                _ALGORITHM,
                headers.get("x-amz-date", amz_date),
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        signing_key = _derive_signing_key(self.secret_key, amz_date, self.region, _SERVICE)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    def _headers_for(self, method: str, amz_date: str, payload_hash: str) -> dict[str, str]:
        host = self._host()
        headers: dict[str, str] = {
            "host": host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
        }
        if self.session_token:
            headers["x-amz-security-token"] = self.session_token
        return headers

    def _host(self) -> str:
        from urllib.parse import urlsplit

        host = urlsplit(self.endpoint).hostname
        if not host:
            raise ValueError(f"endpoint has no hostname: {self.endpoint!r}")
        return host

    def _authorization(
        self,
        method: str,
        path: str,
        query: str,
        headers: dict[str, str],
        body: bytes,
        amz_date: str,
    ) -> str:
        signature = self.sign(method, path, query, headers, body, amz_date)
        scope = f"{amz_date}/{self.region}/{_SERVICE}/aws4_request"
        signed = ";".join(k.lower() for k in sorted(headers))
        return (
            f"{_ALGORITHM} Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed}, Signature={signature}"
        )

    # -- helpers --------------------------------------------------------------

    def _check_remote(self, remote: str) -> str:
        """Validate a storage key and reject path traversal / absolute paths."""
        if not remote or remote.startswith("/"):
            raise ValueError(f"invalid remote key: {remote!r}")
        parts = remote.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"invalid remote key: {remote!r}")
        return remote

    def _path_for(self, remote: str) -> str:
        # URL-encode the key, but keep slashes.
        from urllib.parse import quote

        return f"/{self.bucket}/{quote(remote, safe='/')}"

    def _payload_hash(self, body: bytes) -> str:
        return hashlib.sha256(body).hexdigest()

    async def _request(self, method: str, remote: str, body: bytes) -> httpx.Response:
        key = self._check_remote(remote)
        path = self._path_for(key)
        import datetime as _dt

        amz_date = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        payload_hash = self._payload_hash(body)
        headers = self._headers_for(method, amz_date, payload_hash)
        headers["Authorization"] = self._authorization(method, path, "", headers, body, amz_date)

        url = f"{self.endpoint}{path}"
        request = httpx.Request(method, url, headers=headers, content=body)
        return await self._client.send(request)

    # -- Protocol --------------------------------------------------------------

    async def get(self, remote: str) -> bytes | None:
        resp = await self._request("GET", remote, b"")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content

    async def put(self, remote: str, payload: bytes) -> None:
        if self.readonly:
            raise NotImplementedError("readonly replicator cannot put")
        resp = await self._request("PUT", remote, payload)
        resp.raise_for_status()

    async def exists(self, remote: str) -> bool:
        resp = await self._request("HEAD", remote, b"")
        return resp.status_code == 200


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def _derive_signing_key(secret: str, amz_date: str, region: str, service: str) -> bytes:
    k_date = _hmac(("AWS4" + secret).encode("utf-8"), amz_date.encode("utf-8"))
    k_region = _hmac(k_date, region.encode("utf-8"))
    k_service = _hmac(k_region, service.encode("utf-8"))
    return _hmac(k_service, b"aws4_request")


__all__ = ["S3Replicator"]