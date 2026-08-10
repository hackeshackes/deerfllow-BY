"""Tests for the AWS S3 ``SecretReplicator`` adapter (v1.7 M4).

The adapter talks to S3's object-store surface (GET / PUT / HEAD) with a
hand-rolled AWS Signature V4 (no boto3). HTTP is carried by ``httpx`` with a
``MockTransport`` so every test isolates the signing + request-shaping logic
from the network.
"""

from __future__ import annotations

import httpx
import pytest

from deerflow.admin.s3_replicator import S3Replicator


def _replicator(*, readonly: bool = False, responses: list[httpx.Response] | None = None) -> tuple[S3Replicator, list[dict]]:
    """Build an ``S3Replicator`` over a fake transport that records raw requests."""
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content,
            }
        )
        return responses[0] if responses else httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    repl = S3Replicator(
        endpoint="https://s3.us-east-1.amazonaws.com",
        bucket="secrets-bucket",
        region="us-east-1",
        access_key="AKIATEST",
        secret_key="testsecret",
        readonly=readonly,
        client=client,
    )
    return repl, calls


def _recorded(calls: list[dict], i: int) -> dict:
    return calls[i]


@pytest.mark.asyncio
async def test_get_returns_bytes_on_200():
    repl, _ = _replicator(responses=[httpx.Response(200, content=b"blob-data")])
    body = await repl.get("vaults/primary/secrets.json")
    assert body == b"blob-data"


@pytest.mark.asyncio
async def test_get_returns_none_on_404():
    repl, _ = _replicator(responses=[httpx.Response(404)])
    assert await repl.get("vaults/primary/secrets.json") is None


@pytest.mark.asyncio
async def test_put_uploads_payload():
    repl, calls = _replicator(responses=[httpx.Response(200)])
    await repl.put("vaults/primary/secrets.json", b"payload")
    req = calls[0]
    assert req["method"] == "PUT"
    assert req["body"] == b"payload"
    assert "x-amz-date" in req["headers"]
    assert req["headers"]["authorization"].startswith("AWS4-HMAC-SHA256")

@pytest.mark.asyncio
async def test_put_readonly_refused():
    repl, _ = _replicator(readonly=True)
    with pytest.raises(NotImplementedError):
        await repl.put("vaults/primary/secrets.json", b"x")


@pytest.mark.asyncio
async def test_exists_true_on_200():
    repl, _ = _replicator(responses=[httpx.Response(200)])
    assert await repl.exists("vaults/primary/secrets.json") is True


@pytest.mark.asyncio
async def test_exists_false_on_404():
    repl, _ = _replicator(responses=[httpx.Response(404)])
    assert await repl.exists("vaults/primary/secrets.json") is False


@pytest.mark.asyncio
async def test_remote_path_traversal_rejected():
    repl, _ = _replicator()
    with pytest.raises(ValueError):
        await repl.get("../escape")


def test_signature_is_deterministic():
    """Same inputs produce the same signature (a stable test we can eyeball)."""
    repl = S3Replicator(
        endpoint="https://s3.us-east-1.amazonaws.com",
        bucket="b",
        region="us-east-1",
        access_key="AKIATEST",
        secret_key="secret",
    )
    headers = {"host": "s3.us-east-1.amazonaws.com", "x-amz-date": "20260806T000000Z"}
    sig1 = repl.sign("GET", "/b/key", "", headers, b"", "20260806")
    sig2 = repl.sign("GET", "/b/key", "", headers, b"", "20260806")
    assert sig1 == sig2
    assert isinstance(sig1, str) and len(sig1) == 64