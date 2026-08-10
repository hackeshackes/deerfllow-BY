"""AWS KMS envelope adapter implementing :class:`deerflow.admin.replication.EnvelopeKMS` (v1.7 M4).

Wraps / unwraps a per-vault data key via AWS KMS's JSON HTTP API
(``Encrypt`` / ``Decrypt``), signed with AWS Signature V4. HTTP rides on
``httpx`` (runtime dep); the signing math is standard library only — no boto3.

Response bodies are ``x-amz-json-1.0`` (base64 fields) framed by
``X-Amz-Target``. ``client`` is injectable so tests use a ``MockTransport``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from .replication import EnvelopeKMS

logger = logging.getLogger(__name__)

_SERVICE = "kms"
_ALGORITHM = "AWS4-HMAC-SHA256"
_TARGET_ENCRYPT = "TrentService.Encrypt"
_TARGET_DECRYPT = "TrentService.Decrypt"


class KMSEnvelope(EnvelopeKMS):
    """AWS KMS ``Encrypt`` / ``Decrypt`` envelope adapter."""

    def __init__(
        self,
        *,
        region: str,
        access_key: str,
        secret_key: str,
        key_id: str,
        endpoint: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not region:
            raise ValueError("region is required")
        if not access_key or not secret_key:
            raise ValueError("access_key and secret_key are required")
        if not key_id:
            raise ValueError("key_id is required")
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.key_id = key_id
        self.endpoint = (endpoint.rstrip("/") if endpoint else "") or f"https://kms.{region}.amazonaws.com"
        self._client = client or httpx.AsyncClient()

    # -- signing --------------------------------------------------------------

    def _derive_signing_key(self, amz_date: str) -> bytes:
        def _hmac(key: bytes, data: bytes) -> bytes:
            return hmac.new(key, data, hashlib.sha256).digest()

        k_date = _hmac(("AWS4" + self.secret_key).encode("utf-8"), amz_date.encode("utf-8"))
        k_region = _hmac(k_date, self.region.encode("utf-8"))
        k_service = _hmac(k_region, _SERVICE.encode("utf-8"))
        return _hmac(k_service, b"aws4_request")

    def _signature(self, amz_date: str, canonical_request: bytes) -> str:
        scope = f"{amz_date}/{self.region}/{_SERVICE}/aws4_request"
        string_to_sign = "\n".join(
            [_ALGORITHM, amz_date, scope, hashlib.sha256(canonical_request).hexdigest()]
        )
        key = self._derive_signing_key(amz_date)
        return hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    def _headers(self, amz_date: str, payload_hash: str, target: str) -> dict[str, str]:
        from urllib.parse import urlsplit

        host = urlsplit(self.endpoint).hostname or self.endpoint
        return {
            "host": host,
            "x-amz-date": amz_date,
            "x-amz-target": target,
            "content-type": "application/x-amz-json-1.0",
            "x-amz-content-sha256": payload_hash,
        }

    def _authorization(self, headers: dict[str, str], amz_date: str) -> str:
        scope = f"{amz_date}/{self.region}/{_SERVICE}/aws4_request"
        signed = ";".join(k.lower() for k in sorted(headers))
        payload_hash = headers["x-amz-content-sha256"]
        canonical_headers = "".join(f"{k.lower()}:{headers[k].strip()}\n" for k in sorted(headers))
        canonical_request = "\n".join(
            ["POST", "/", "", canonical_headers, signed, payload_hash]
        )
        signature = self._signature(amz_date, canonical_request.encode("utf-8"))
        return (
            f"{_ALGORITHM} Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed}, Signature={signature}"
        )

    async def _call(self, target: str, payload: dict[str, Any]) -> dict[str, Any]:
        import datetime as _dt

        tree = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        body = json.dumps(payload).encode("utf-8")
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = self._headers(tree, payload_hash, target)
        headers["Authorization"] = self._authorization(headers, tree)
        request = httpx.Request("POST", self.endpoint + "/", headers=headers, content=body)
        resp = await self._client.send(request)
        resp.raise_for_status()
        return json.loads(resp.content)

    # -- Protocol --------------------------------------------------------------

    async def wrap(self, data_key: bytes) -> bytes:
        resp = await self._call(
            _TARGET_ENCRYPT,
            {"KeyId": self.key_id, "Plaintext": base64.b64encode(data_key).decode("ascii")},
        )
        blob = resp.get("CiphertextBlob")
        if not blob:
            raise RuntimeError(f"AWS KMS Encrypt returned no CiphertextBlob: {resp}")
        return base64.b64decode(blob)

    async def unwrap(self, wrapped_key: bytes) -> bytes:
        resp = await self._call(
            _TARGET_DECRYPT,
            {"CiphertextBlob": base64.b64encode(wrapped_key).decode("ascii")},
        )
        plain = resp.get("Plaintext")
        if not plain:
            raise RuntimeError(f"AWS KMS Decrypt returned no Plaintext: {resp}")
        return base64.b64decode(plain)


__all__ = ["KMSEnvelope"]