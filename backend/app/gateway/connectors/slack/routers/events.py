"""Slack webhook events endpoint (v1.6.1 P0 follow-up).

Mounted at ``/api/connectors/slack/events``. Handles two request
shapes from Slack:

1. **URL-verification handshake** (unauthenticated by Slack convention):
   responds 200 with the ``challenge`` echoed back as plain text.
2. **Event callback** (HMAC-signed): verifies the v0 signature over
   the raw request body before delegating to the
   ``SlackConnector.receive_webhook``.

The signing secret is read from ``app.state.slack_signing_secret``
which the lifespan (Task C3+) populates from a configuration source;
if it's missing the endpoint refuses everything except the URL
verification handshake (which Slack requires us to echo).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..signing import is_url_verification

router = APIRouter(prefix="/api/connectors/slack", tags=["slack"])


async def _read_body(request: Request) -> bytes:
    return await request.body()


def _get_signing_secret(request: Request) -> str | None:
    """Read the signing secret off ``app.state`` without making the
    endpoint brittle to lifespan ordering — return ``None`` when the
    lifespan didn't populate it yet (e.g. tests that build the app
    directly)."""
    app = request.app
    return getattr(app.state, "slack_signing_secret", None)


def _get_connector(request: Request):
    """Locate the registered SlackConnector; raise 503 when missing so
    operational mistakes surface cleanly in logs rather than
    silently dropping events."""
    app = request.app
    conn = getattr(app.state, "slack_connector", None)
    if conn is None:
        raise HTTPException(status_code=503, detail="slack connector not configured")
    return conn


@router.post("/events")
async def slack_events(request: Request) -> Any:
    body = await _read_body(request)

    # URL verification: Slack sends this once at app install without
    # an HMAC signature. Reply 200 with the challenge so Slack
    # trusts the endpoint URL.
    try:
        parsed = json.loads(body.decode())
    except (ValueError, UnicodeDecodeError):
        parsed = {}
    if is_url_verification(parsed):
        challenge = parsed.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            raise HTTPException(status_code=400, detail="missing challenge")
        # Slack's handshake spec returns plain-text body; we
        # deliberately do NOT use response_model=JSON here.
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(challenge, status_code=200)

    # Everything else is HMAC-signed. Verify before touching the
    # connector to keep forged payloads from leaking into the
    # runnable pipeline.
    from ..signing import SlackSignatureVerifier

    secret = _get_signing_secret(request)
    verifier = SlackSignatureVerifier(secret)
    if not verifier.verify(
        headers=dict(request.headers),
        body=body,
    ):
        raise HTTPException(status_code=401, detail="invalid slack signature")

    conn = _get_connector(request)
    messages = await conn.receive_webhook(parsed)
    return {
        "messages": [
            {"text": m.text, "target": m.target, "metadata": m.metadata}
            for m in messages
        ]
    }
