"""Slack connector (v1.6.1, Task C3).

Implements `BaseConnector` against the Slack Web API:

* Outbound: ``chat.postMessage`` with bearer auth (``xoxb-...``).
* Inbound: Slack Events API ``event_callback`` → ``ConnectorMessage``;
  URL-verification challenge is handled in a separate helper so the
  bridge can short-circuit it before delegating to the connector.
* Health: ``auth.test``.

Socket Mode (``apps.connections.open`` + WebSocket subscription) is
explicitly out of scope for v1.6.1 — it is a much larger surface (TLS,
reconnect, ack) and was marked P2 in the v1.6.x plan; HTTP events are
sufficient for the spec'd P1 integration.

Concurrency: ``SlackConnector`` keeps a single ``httpx.AsyncClient``
for the lifetime of the instance; the registry owns the instance, and
callers close it via ``aclose()`` at shutdown. Token refresh is not
needed because slack bot tokens are long-lived ``xoxb-...`` strings
issued once at install time.
"""

from __future__ import annotations

import logging

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


class SlackConnector(BaseConnector):
    name = "slack"
    display_name = "Slack"

    def __init__(self, bot_token: str, timeout: float = 10.0) -> None:
        if not bot_token:
            raise ValueError("slack connector requires non-empty bot_token")
        self._bot_token = bot_token
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=SLACK_API_BASE,
            headers={"Authorization": f"Bearer {bot_token}"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------------------------------------------------------------- send
    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        channel = message.target.get("channel") or message.target.get("chat_id")
        if not channel:
            return ConnectorResponse(
                success=False,
                error="slack send requires channel in message.target",
            )
        try:
            resp = await self._client.post(
                "/chat.postMessage",
                json={"channel": channel, "text": message.text},
            )
            data = resp.json()
            if data.get("ok") is True:
                return ConnectorResponse(
                    success=True,
                    external_id=str(data.get("ts") or "") or None,
                    raw=data,
                )
            return ConnectorResponse(
                success=False,
                error=f"slack api error: {data.get('error') or 'unknown'}",
                raw=data,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("slack send failed")
            return ConnectorResponse(success=False, error=str(exc))

    # ------------------------------------------------------- inbound events
    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        # Only translate "message" events into runnable chat messages.
        # Reaction_added, user_typing, file_shared etc. are intentionally
        # dropped — the lead agent only consumes human text turns.
        if not isinstance(payload, dict):
            return []
        if payload.get("type") != "event_callback":
            # url_verification and other non-event payloads emit zero
            # messages; the bridge handles the verification challenge
            # via verify_challenge_event() before delegating here.
            return []
        event = payload.get("event") or {}
        if event.get("type") != "message":
            return []
        text = event.get("text")
        channel = event.get("channel")
        if not isinstance(text, str) or not text:
            return []
        if not isinstance(channel, str) or not channel:
            return []
        # Skip bot/self messages so the bot does not echo its own output
        # back through the runnable pipeline.
        if event.get("subtype") in {"bot_message", "channel_join", "thread_broadcast"}:
            return []
        return [
            ConnectorMessage(
                text=text,
                target={"channel": channel, "user_id": event.get("user") or ""},
                metadata={
                    "slack_event_type": event.get("type"),
                    "slack_event_ts": event.get("ts") or "",
                },
            )
        ]

    # ------------------------------------------------- url-verification helper
    def verify_challenge_event(self, payload: dict) -> str | None:
        """Return the Slack ``challenge`` string for a URL-verification
        event, or ``None`` if the payload is not a verification request.

        The webhook bridge calls this BEFORE delegating to
        ``receive_webhook`` so a 200 OK with the echoed challenge is
        delivered to Slack's handshake, not a 200 with no body.
        """
        if not isinstance(payload, dict):
            return None
        if payload.get("type") != "url_verification":
            return None
        challenge = payload.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            return None
        return challenge

    # -------------------------------------------------------- health check
    async def health_check(self) -> bool:
        """``auth.test`` returns ``{"ok": True}`` iff the bot token is
        still valid; returns False on any error or ``ok: False`` body."""
        try:
            resp = await self._client.post("/auth.test", json={})
            data = resp.json()
            return bool(data.get("ok") is True)
        except Exception:  # noqa: BLE001
            return False
