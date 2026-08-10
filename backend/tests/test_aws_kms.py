"""Tests for the AWS KMS ``EnvelopeKMS`` adapter (v1.7 M4).

``KMSEnvelope`` wraps / unwraps a per-vault data key via AWS KMS's JSON HTTP
API (``Encrypt``/``Decrypt``), signed with Signature V4. HTTP rides on ``httpx``
with a ``MockTransport`` returning hand-encoded base64 responses, so the whole
module is unit-testable without any real cloud credentials.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from deerflow.admin.aws_kms import KMSEnvelope


def _encoded(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _fake_transport(*, wrap_key: bytes, unwrap_plain: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        req = json.loads(request.content)
        target = request.headers.get("x-amz-target", "")
        if "Encrypt" in target:
            return httpx.Response(200, json={"CiphertextBlob": _encoded(wrap_key)})
        if "Decrypt" in target:
            assert req.get("CiphertextBlob") == _encoded(wrap_key)
            return httpx.Response(200, json={"Plaintext": _encoded(unwrap_plain)})
        return httpx.Response(400)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _envelope(client: httpx.AsyncClient) -> KMSEnvelope:
    return KMSEnvelope(
        region="us-east-1",
        access_key="AKIATEST",
        secret_key="secret",
        key_id="arn:aws:kms:us-east-1:123456789012:key/abc",
        client=client,
    )


@pytest.mark.asyncio
async def test_wrap_returns_ciphertext_blob():
    client = _fake_transport(wrap_key=b"cipher-blob", unwrap_plain=b"")
    kms = _envelope(client)
    assert await kms.wrap(b"data-key") == b"cipher-blob"


@pytest.mark.asyncio
async def test_unwrap_returns_plaintext():
    wrapped = b"cipher-blob"
    client = _fake_transport(wrap_key=wrapped, unwrap_plain=b"data-key")
    kms = _envelope(client)
    assert await kms.unwrap(wrapped) == b"data-key"


@pytest.mark.asyncio
async def test_wrap_round_trips_with_unwrap():
    """Encrypt then decrypt a data key via the fake KMS returns the original."""
    data_key = b"a-secret-data-key-here"
    client = _fake_transport(wrap_key=b"wrapped", unwrap_plain=data_key)
    kms = _envelope(client)
    wrapped = await kms.wrap(data_key)
    assert await kms.unwrap(wrapped) == data_key