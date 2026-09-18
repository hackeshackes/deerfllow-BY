"""GCS replicator: SigV4 determinism + MockTransport behavior."""
# ruff: noqa: E701,E702
from __future__ import annotations

import httpx
import pytest

from deerflow.admin.gcs_replicator import GCSReplicator


def _rep(**kw):
    base = dict(bucket="b", access_key="AKID", secret_key="sk", region="auto")
    base.update(kw); return GCSReplicator(**base)

def test_gcs_signature_is_deterministic():
    h = {"host": "storage.googleapis.com"}
    s1 = _rep()._signature("PUT", "/b/vault.enc", "", h, b"data", "20260806T000000Z")
    s2 = _rep()._signature("PUT", "/b/vault.enc", "", h, b"data", "20260806T000000Z")
    assert s1 == s2 and len(s1) == 64

def test_gcs_authorization_has_scope():
    auth = _rep()._authorization("PUT", "/b/v1", {"host": "x"}, b"v", "20260806T000000Z")
    assert auth.startswith("AWS4-HMAC-SHA256 Credential=AKID/20260806/auto/s3/aws4_request")
    assert "Signature=" in auth

@pytest.mark.asyncio
async def test_gcs_missing_get_returns_none():
    r = _rep(client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(404, request=req))))
    assert await r.get("v1") is None

@pytest.mark.asyncio
async def test_gcs_put_roundtrip_and_exists():
    got = {}
    def handler(req):
        if req.method == "PUT": got["body"] = req.content; return httpx.Response(200, request=req)
        if req.method == "HEAD": return httpx.Response(200 if req.url.path.endswith("v1") else 404, request=req)
        return httpx.Response(200, content=got.get("body", b""), request=req)
    r = _rep(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await r.put("v1", b"payload")
    assert got["body"] == b"payload"
    assert await r.exists("v1") is True

@pytest.mark.asyncio
async def test_gcs_readonly_blocks_put():
    r = _rep(readonly=True, client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, request=req))))
    with pytest.raises(RuntimeError): await r.put("v1", b"x")
