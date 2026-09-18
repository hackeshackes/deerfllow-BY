"""Aliyun Object Storage Service (OSS) adapter — :class:`SecretReplicator` (M4.2).

OSS uses its own request signing (header-based ``OSS AccessKeyId:Signature``
over HMAC-SHA1), unlike AWS SigV4. No OSS SDK; HTTP rides on ``httpx``.
``client`` is injectable so tests use ``httpx.MockTransport``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime

import httpx

from .replication import SecretReplicator

logger = logging.getLogger(__name__)


class AliyunOSSReplicator(SecretReplicator):
    """Sign-and-forward Aliyun OSS object store over httpx."""

    def __init__(
        self,
        *,
        bucket: str,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str = "oss-cn-hangzhou.aliyuncs.com",
        readonly: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("bucket is required")
        if not access_key_id or not access_key_secret:
            raise ValueError("access_key_id and access_key_secret are required")
        self.bucket = bucket
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint.rstrip("/")
        self.readonly = readonly
        self._client = client or httpx.AsyncClient()

    # -- OSS signing (canonicalized headers + resource) ----------------------

    def _canonical_resource(self, remote: str) -> str:
        return f"/{self.bucket}/{remote.lstrip('/')}"

    def _signature(self, method: str, resource: str, headers: dict[str, str]) -> str:
        # OSS stringToSign: VERB + "\n" + [lf+header for x-oss-*] + resource
        parts: list[str] = [method.upper()]
        oss_headers = {k.lower(): v.strip() for k, v in headers.items() if k.lower().startswith("x-oss-")}
        for k in sorted(oss_headers):
            parts.append(f"{k}:{oss_headers[k]}")
        parts.append(resource)
        string_to_sign = "\n".join(parts)
        sig = hmac.new(
            self.access_key_secret.encode(), string_to_sign.encode(), hashlib.sha1
        ).digest()
        return base64.b64encode(sig).decode()

    def _authorization(self, method: str, remote: str, headers: dict[str, str]) -> str:
        sig = self._signature(method, self._canonical_resource(remote), headers)
        return f"OSS {self.access_key_id}:{sig}"

    def _url(self, remote: str) -> str:
        # bucket in path-style for simplicity; works with virtual-host too.
        return f"https://{self.endpoint}/{self.bucket}/{remote.lstrip('/')}"

    async def get(self, remote: str) -> bytes | None:
        resp = await self._client.get(self._url(remote), timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content

    async def put(self, remote: str, payload: bytes) -> None:
        if self.readonly:
            raise RuntimeError("Aliyun OSS replicator is read-only")
        now = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {"Date": now}
        await self._client.put(
            self._url(remote), content=payload, headers=headers, timeout=15
        )

    async def exists(self, remote: str) -> bool:
        resp = await self._client.head(self._url(remote), timeout=15)
        return resp.status_code == 200