"""Aliyun OSS replicator: HMAC-SHA1 signing + MockTransport behavior."""
# ruff: noqa: E701,E702
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx
import pytest

from deerflow.admin.aliyun_oss_replicator import AliyunOSSReplicator


def _rep(**kw):
    base = dict(bucket="bkt", access_key_id="AKID", access_key_secret="secret")
    base.update(kw); return AliyunOSSReplicator(**base)

def test_aliyun_signature_matches_manual_hmac():
    r = _rep()
    resource = r._canonical_resource("vault.enc")
    headers = {"x-oss-meta-k": "v"}
    their = r._signature("PUT", resource, headers)
    expected_lines = ["PUT", "x-oss-meta-k:v", resource]
    expected = base64.b64encode(hmac.new(b"secret", "\n".join(expected_lines).encode(), hashlib.sha1).digest()).decode()
    assert their == expected

def test_aliyun_authorization_has_oss_prefix():
    auth = _rep()._authorization("PUT", "vault.enc", {})
    assert auth.startswith("OSS AKID:")

@pytest.mark.asyncio
async def test_aliyun_get_missing_404():
    def h(req): return httpx.Response(404, request=req)
    r = _rep(client=httpx.AsyncClient(transport=httpx.MockTransport(h)))
    assert await r.get("v1") is None

@pytest.mark.asyncio
async def test_aliyun_put_roundtrip_and_exists():
    got={}
    def h(req):
        if req.method=="PUT": got["body"]=req.content; return httpx.Response(200, request=req)
        if req.method=="HEAD": return httpx.Response(200 if req.url.path.endswith("v1") else 404, request=req)
        return httpx.Response(200, content=got.get("body",b""), request=req)
    r=_rep(client=httpx.AsyncClient(transport=httpx.MockTransport(h)))
    await r.put("v1", b"payload")
    assert got["body"]==b"payload"
    assert await r.exists("v1") is True

@pytest.mark.asyncio
async def test_aliyun_readonly_blocks_put():
    r=_rep(readonly=True, client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, request=req))))
    with pytest.raises(RuntimeError): await r.put("v1", b"x")
