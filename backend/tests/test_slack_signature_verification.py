"""Tests for Slack webhook signature verification (v1.6.1 P0 follow-up).

The Slack Events API signs every inbound POST:

    v0={timestamp}:{body}

Where ``timestamp`` is the value of ``X-Slack-Request-Timestamp`` and
``body`` is the raw request body bytes. The signature header is
``X-Slack-Signature`` and the algorithm is HMAC-SHA256 keyed by the
signing secret you get from the Slack App dashboard. Verified within
~5 minutes of the current time (replay defense) per Slack's docs.

These tests lock down both the verifier module and the FastAPI
endpoint behavior:

* happy path: correctly signed request → 200, connector invoked
* wrong secret → 401
* missing timestamp → 401
* missing signature → 401
* stale timestamp (>5 min) → 401 (replay defense)
* URL verification challenge (no signature required) → 200 + echoed challenge
* tampered body → 401
"""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.connectors.integrations.builtin import register_builtin_connectors
from app.gateway.connectors.registry import ConnectorRegistry
from app.gateway.connectors.slack.signing import (
    SlackSignatureVerifier,
    is_url_verification,
    verify_slack_signature,
)

SIGNING_SECRET = "test-signing-secret-xyz"
TIMESTAMP_OK = str(int(time.time()))
TIMESTAMP_STALE = str(int(time.time()) - 600)  # 10 minutes ago


def _sign(secret: str, timestamp: str, body: bytes) -> str:
    """Reproduce Slack's signature algorithm."""
    base = f"v0={timestamp}:".encode() + body
    digest = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


# ---- Pure verifier tests ----


def test_verify_url_verification_payload_with_no_headers_returns_challenge():
    """Slack sends an unencrypted URL-verification request at the
    handshake; it has no signature header and must NOT be rejected."""
    payload = {"type": "url_verification", "challenge": "abc-123"}
    assert is_url_verification(payload) is True
    assert verify_slack_signature(
        signing_secret=SIGNING_SECRET,
        headers={},
        body=b'{"type":"url_verification","challenge":"abc-123"}',
        timestamp_header=None,
        signature_header=None,
        now=TIMESTAMP_OK,
    ) is True
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=b'{"type":"url_verification","challenge":"abc-123"}',
            timestamp_header=TIMESTAMP_OK,
            signature_header=None,
            now=TIMESTAMP_OK,
        )
        is True
    )


def test_verify_accepts_correctly_signed_event_callback():
    body = (
        b'{"type":"event_callback","event":{"type":"message",'
        b'"text":"hi","channel":"C1","user":"U1"}}'
    )
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, body)
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=body,
            timestamp_header=TIMESTAMP_OK,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is True
    )


def test_verify_rejects_wrong_secret():
    body = b'{"type":"event_callback","event":{}}'
    sig = _sign("wrong-secret", TIMESTAMP_OK, body)
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=body,
            timestamp_header=TIMESTAMP_OK,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is False
    )


def test_verify_rejects_tampered_body():
    body = b'{"type":"event_callback","event":{"type":"message","text":"hi"}}'
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, body)
    tampered = body.replace(b"hi", b"pwned")
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=tampered,
            timestamp_header=TIMESTAMP_OK,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is False
    )


def test_verify_rejects_stale_timestamp():
    body = b'{"type":"event_callback","event":{}}'
    sig = _sign(SIGNING_SECRET, TIMESTAMP_STALE, body)
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=body,
            timestamp_header=TIMESTAMP_STALE,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is False
    )


def test_verify_rejects_missing_signature_header():
    body = b'{"type":"event_callback","event":{}}'
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=body,
            timestamp_header=TIMESTAMP_OK,
            signature_header=None,
            now=TIMESTAMP_OK,
        )
        is False
    )


def test_verify_rejects_missing_timestamp_header():
    body = b'{"type":"event_callback","event":{}}'
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, body)
    assert (
        verify_slack_signature(
            signing_secret=SIGNING_SECRET,
            headers={},
            body=body,
            timestamp_header=None,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is False
    )


def test_verifier_object_wraps_callable():
    """SlackSignatureVerifier is the object form of the verifier —
    callable as ``verifier.verify(headers, body, now=...)``.
    """
    v = SlackSignatureVerifier(SIGNING_SECRET)
    body = b'{"type":"event_callback","event":{}}'
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, body)
    assert (
        v.verify(
            headers={},
            body=body,
            timestamp_header=TIMESTAMP_OK,
            signature_header=sig,
            now=TIMESTAMP_OK,
        )
        is True
    )


def test_verifier_object_rejects_empty_secret_at_construction():
    with pytest.raises(ValueError, match="signing_secret"):
        SlackSignatureVerifier("")


# ---- FastAPI endpoint test (HMAC wired end-to-end) ----


def _build_slack_router(signing_secret: str | None) -> FastAPI:
    """Build a tiny FastAPI app with the slack events endpoint mounted
    and a SlackConnector registered against the bridge."""
    from app.gateway.connectors.slack.routers.events import router as slack_router

    app = FastAPI()
    app.include_router(slack_router)

    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"slack": {"bot_token": "xoxb-test"}},
    )
    app.state.slack_signing_secret = signing_secret
    app.state.slack_connector = reg.get("slack")
    return app


def _slack_client(app: FastAPI, body: bytes, ts: str, sig: str) -> TestClient:
    return TestClient(
        app,
        headers={
            "X-Slack-Request-Timestamp": ts,
            "X-Slack-Signature": sig,
            "Content-Type": "application/json",
        },
    )


def test_endpoint_accepts_signed_event_callback_and_invokes_connector():
    app = _build_slack_router(SIGNING_SECRET)
    body = (
        b'{"type":"event_callback","event":{"type":"message",'
        b'"text":"hello slack","channel":"C1","user":"U1"}}'
    )
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, body)
    client = _slack_client(app, body, TIMESTAMP_OK, sig)
    resp = client.post("/api/connectors/slack/events", content=body)
    assert resp.status_code == 200, resp.text
    # The Slack connector returned one message for this event.
    body_resp = resp.json()
    assert body_resp["messages"][0]["text"] == "hello slack"


def test_endpoint_rejects_unsigned_event_callback_with_401():
    app = _build_slack_router(SIGNING_SECRET)
    body = (
        b'{"type":"event_callback","event":{"type":"message",'
        b'"text":"forged","channel":"C1","user":"U1"}}'
    )
    # No signature / timestamp headers.
    client = TestClient(app)
    resp = client.post("/api/connectors/slack/events", content=body)
    assert resp.status_code == 401, resp.text


def test_endpoint_accepts_url_verification_with_200_and_echoes_challenge():
    """The Slack handshake is unencrypted (no signature); on success
    the endpoint MUST respond 200 with the challenge as plain text
    so Slack completes the URL verification."""
    app = _build_slack_router(SIGNING_SECRET)
    body = b'{"type":"url_verification","challenge":"handshake-abc"}'
    client = TestClient(app)
    resp = client.post("/api/connectors/slack/events", content=body)
    assert resp.status_code == 200, resp.text
    # Plain text body, not JSON — Slack expects raw text here.
    assert resp.text == "handshake-abc"


def test_endpoint_rejects_signed_request_when_secret_misconfigured():
    """A correctly-signed request with a body must be rejected if the
    gateway has no signing_secret configured (because comparing
    anything against '' is undefined and we refuse)."""
    app = _build_slack_router(None)  # no secret configured
    body = (
        b'{"type":"event_callback","event":{"type":"message","text":"hi","channel":"C","user":"U"}}'
    )
    # Construct a perfectly valid signature with a known secret.
    sig = _sign("some-other-secret", TIMESTAMP_OK, body)
    client = _slack_client(app, body, TIMESTAMP_OK, sig)
    resp = client.post("/api/connectors/slack/events", content=body)
    assert resp.status_code == 401, resp.text


def test_endpoint_rejects_tampered_body_with_401():
    app = _build_slack_router(SIGNING_SECRET)
    original = (
        b'{"type":"event_callback","event":{"type":"message","text":"hi","channel":"C","user":"U"}}'
    )
    sig = _sign(SIGNING_SECRET, TIMESTAMP_OK, original)
    tampered = original.replace(b"hi", b"pwned")
    client = _slack_client(app, tampered, TIMESTAMP_OK, sig)
    resp = client.post("/api/connectors/slack/events", content=tampered)
    assert resp.status_code == 401, resp.text


def test_endpoint_rejects_stale_timestamp_with_401():
    app = _build_slack_router(SIGNING_SECRET)
    body = b'{"type":"event_callback","event":{}}'
    sig = _sign(SIGNING_SECRET, TIMESTAMP_STALE, body)
    client = _slack_client(app, body, TIMESTAMP_STALE, sig)
    resp = client.post("/api/connectors/slack/events", content=body)
    assert resp.status_code == 401, resp.text
