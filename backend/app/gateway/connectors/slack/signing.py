"""Slack webhook signature verification (v1.6.1 P0 follow-up).

The Slack Events API signs every inbound POST with HMAC-SHA256:

    base_string   = "v0=" + timestamp + ":" + raw_body
    signature     = "v0=" + hex(hmac_sha256(signing_secret, base_string))

Where ``timestamp`` is the value of ``X-Slack-Request-Timestamp``
(seconds since epoch) and ``raw_body`` is the exact bytes Slack
sent (before any JSON parsing). The corresponding header is
``X-Slack-Signature``.

The URL-verification handshake (sent once at app install) is NOT
signed — it has type ``url_verification`` and is the only
unauthenticated request the endpoint accepts.

Replay defense: Slack requires verification within ~5 minutes of
the current time. ``verify_slack_signature`` accepts an explicit
``now`` so tests can pin the clock.

This module exists in addition to ``webhook.py`` (which still uses
static shared secrets for connectors like Email that don't sign).
Slack is the first platform to opt into HMAC verification; future
signing protocols can ship as sibling modules without changing the
bridge interface.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

SLACK_MAX_TIMESTAMP_DRIFT_SECONDS = 5 * 60  # 5 minutes (Slack recommendation)

_SLACK_TS_HEADER = "x-slack-request-timestamp"
_SLACK_SIG_HEADER = "x-slack-signature"
_URL_VERIFICATION_TYPE = "url_verification"


def is_url_verification(payload: Any) -> bool:
    """True iff the payload is a Slack URL-verification handshake."""
    if not isinstance(payload, dict):
        return False
    return payload.get("type") == _URL_VERIFICATION_TYPE


def _header_value(headers: dict, name: str) -> str | None:
    """Headers are case-insensitive — accept any casing."""
    if not headers:
        return None
    for k, v in headers.items():
        if isinstance(k, str) and k.lower() == name:
            return v if isinstance(v, str) else None
    return None


def _compute_signature(signing_secret: str, timestamp: str, body: bytes) -> str:
    """Compute the v0 signature Slack would have emitted."""
    base = f"v0={timestamp}:".encode() + body
    digest = hmac.new(
        signing_secret.encode(), base, hashlib.sha256
    ).hexdigest()
    return f"v0={digest}"


def _constant_time_equals(a: str, b: str) -> bool:
    """Constant-time string compare — never short-circuit on length
    mismatch; pad to the longer length so the timing depends on the
    bigger of the two strings only."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    a_bytes = a.encode()
    b_bytes = b.encode()
    diff = len(a_bytes) ^ len(b_bytes)
    for x, y in zip(a_bytes, b_bytes):
        diff |= x ^ y
    return diff == 0


def verify_slack_signature(
    *,
    signing_secret: str,
    headers: dict,
    body: bytes,
    timestamp_header: str | None = None,
    signature_header: str | None = None,
    now: str | None = None,
) -> bool:
    """Return True iff the request is a legitimate Slack request.

    Returns True unconditionally for URL-verification handshakes —
    those have no signature by design. Refuses everything else if
    the gateway has no signing_secret configured (so an
    unconfigured deployment cannot accidentally accept signed
    requests with a guessed secret).

    Explicit ``timestamp_header`` / ``signature_header`` overrides
    let callers pipe from request headers under any naming
    convention (ASGI headers are lowercased). The function falls
    back to ``headers`` lookup if either override is missing.
    """
    # URL verification is unauthenticated by Slack convention.
    try:
        parsed = json.loads(body.decode())
    except (ValueError, UnicodeDecodeError):
        parsed = None
    if is_url_verification(parsed):
        return True

    if not signing_secret:
        # Refuse to verify when no signing secret is configured —
        # comparing any signature against the empty string is
        # meaningless and we never want to silently allow it.
        return False

    ts = timestamp_header or _header_value(headers, _SLACK_TS_HEADER)
    sig = signature_header or _header_value(headers, _SLACK_SIG_HEADER)
    if not ts or not sig:
        return False

    # Replay defense.
    try:
        ts_int = int(ts)
        now_int = int(now) if now is not None else int(time.time())
    except ValueError:
        return False
    if abs(now_int - ts_int) > SLACK_MAX_TIMESTAMP_DRIFT_SECONDS:
        return False

    expected = _compute_signature(signing_secret, ts, body)
    return _constant_time_equals(expected, sig)


class SlackSignatureVerifier:
    """Object-form verifier. The webhook bridge / FastAPI dependency
    can hold a verifier instance and call ``.verify(...)`` instead of
    passing the signing secret around. Mirrors how a future
    FeishuVerifier or DingTalkVerifier would be wired.
    """

    def __init__(self, signing_secret: str | None) -> None:
        if signing_secret is not None and not isinstance(signing_secret, str):
            raise ValueError(
                f"signing_secret must be a string or None; got {type(signing_secret).__name__}"
            )
        if signing_secret == "":
            raise ValueError("signing_secret must be a non-empty string when provided")
        self._secret = signing_secret or None

    def verify(
        self,
        *,
        headers: dict,
        body: bytes,
        timestamp_header: str | None = None,
        signature_header: str | None = None,
        now: str | None = None,
    ) -> bool:
        return verify_slack_signature(
            signing_secret=self._secret or "",
            headers=headers,
            body=body,
            timestamp_header=timestamp_header,
            signature_header=signature_header,
            now=now,
        )

    @property
    def configured(self) -> bool:
        return self._secret is not None
