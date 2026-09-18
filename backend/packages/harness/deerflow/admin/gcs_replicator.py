"""Google Cloud Storage object-store adapter — :class:`SecretReplicator` (M4.2).

GCS exposes an S3-compatible XML API (SigV4 with service name ``s3`` at
``storage.googleapis.com``), so this adapter reuses the AWS Signature V4
signing pattern used by :mod:`s3_replicator` but targets GCS. No GCS SDK; HTTP
rides on ``httpx`` (project runtime dep). ``client`` is injectable so tests
use ``httpx.MockTransport`` with no network.
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


class GCSReplicator(SecretReplicator):
    """Sign-and-forward GCS (XML API) object store over httpx."""

    def __init__(
        self,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        # GCS XML API SigV4 mangles the host; default is the regional endpoint.
        endpoint: str = "https://storage.googleapis.com",
        region: str = "auto",
        session_token: str | None = None,
        readonly: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("bucket is required")
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

    # -- SigV4 (GCS XML API service name "s3") -------------------------------

    def _signature(
        self,
        method: str,
        path: str,
        query: str,
        headers: dict[str, str],
        body: bytes,
        amz_date: str,
    ) -> str:
        plan_date = amz_date[:8]
        scope = f"{plan_date}/{self.region}/{_SERVICE}/aws4_request"
        canonical_headers = "".join(
            f"{k.lower()}:{headers[k].strip()}\n" for k in sorted(headers)
        )
        signed_headers = ";".join(k.lower() for k in sorted(headers))
        payload_hash = hashlib.sha256(body).hexdigest()
        canonical = "\n".join(
            [method.upper(), path, query, canonical_headers, signed_headers, payload_hash]
        )
        string_to_sign = "\n".join(
            [_ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()]
        )
        k_date = hmac.new(("AWS4" + self.secret_key).encode(), plan_date.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, self.region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, _SERVICE.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
        return hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    def _authorization(
        self, method: str, path: str, headers: dict[str, str], body: bytes, amz_date: str
    ) -> str:
        query = ""
        scope = f"{amz_date[:8]}/{self.region}/{_SERVICE}/aws4_request"
        sig = self._signature(method, path, query, headers, body, amz_date)
        signed_headers = ";".join(k.lower() for k in sorted(headers))
        return (
            f"{_ALGORITHM} Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={sig}"
        )

    def _object_url(self, remote: str) -> str:
        return f"{self.endpoint}/{self.bucket}/{remote.lstrip('/')}"

    async def get(self, remote: str) -> bytes | None:
        url = self._object_url(remote)
        headers = {}
        resp = await self._client.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content

    async def put(self, remote: str, payload: bytes) -> None:
        if self.readonly:
            raise RuntimeError("GCS replicator is read-only")
        url = self._object_url(remote)
        headers = {"Host": url.split("//")[1].split("/")[0]}
        await self._client.put(url, content=payload, headers=headers, timeout=15)

    async def exists(self, remote: str) -> bool:
        url = self._object_url(remote)
        resp = await self._client.head(url, timeout=15)
        return resp.status_code == 200