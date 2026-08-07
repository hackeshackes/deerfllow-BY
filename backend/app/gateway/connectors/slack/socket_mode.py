"""Slack Socket Mode (v1.7 M5).

Socket Mode avoids a public webhook URL entirely: the connector opens an
**outbound-only** WebSocket to Slack via ``apps.connections.open`` (Slack SDK's
``SocketModeClient``). Events arrive over that socket and are dispatched through
the same ``event → ConnectorMessage`` translation the webhook mode uses.

The reconnect loop and frame dispatch are **transport-agnostic** so they can be
unit-tested against a fake transport (no real socket in tests)::

* :class:`SocketTransport` — the seam (connect / recv / close). The production
  adapter wraps ``slack_sdk.socket_mode.SocketModeClient``.
* :class:`ReconnectLoop` — connect → handle frames → on drop, reconnect with
  exponential backoff + jitter, bounded by ``max_attempts``.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from ..base import ConnectorMessage

logger = logging.getLogger(__name__)

# Sentinel pushed on close so ``recv()`` returns None to the reconnect loop.
_CLOSE_SENTINEL = object()


class SocketTransport(Protocol):
    """Minimal outbound WebSocket surface (testable seam)."""

    async def connect(self) -> None: ...
    async def recv(self) -> dict[str, Any] | None: ...
    async def close(self) -> None: ...


class ReconnectLoop:
    """Connect, dispatch frames, and reconnect with exponential backoff.

    ``recv() -> None`` signals a dropped connection; the loop waits an
    exponentially-backed-off delay (plus jitter) before reconnecting. A
    ``max_attempts`` cap bounds reconnects so a closed-network test models a
    bounded window instead of spinning forever.

    ``sleep`` is injectable so tests run instantly without real backoff waits.
    """

    def __init__(
        self,
        transport: SocketTransport,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
        *,
        base_backoff: float = 0.5,
        max_backoff: float = 30.0,
        max_attempts: int | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.transport = transport
        self.handler = handler
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.max_attempts = max_attempts
        self._sleep = sleep or asyncio.sleep
        self._rng = rng or random.Random()
        self.reconnect_count = 0
        self.stop_requested = False

    async def stop(self) -> None:
        if not self.stop_requested:
            self.stop_requested = True
            await self.transport.close()

    async def run(self) -> None:
        attempt = 0  # consecutive failed connect/read attempts
        while not self.stop_requested:
            if self.max_attempts is not None and attempt >= self.max_attempts:
                logger.warning("Socket reconnect giving up after %s attempts", attempt)
                return
            try:
                await self.transport.connect()
                healthy = False
                while not self.stop_requested:
                    frame = await self.transport.recv()
                    if frame is None:  # EOF / drop
                        break
                    healthy = True  # a real exchange → reset backoff next time
                    await self._dispatch(frame)
                if healthy:
                    attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - connect/read error
                logger.info("Socket connection dropped; reconnecting", exc_info=True)
            self.reconnect_count += 1
            await self._sleep(self._next_delay(attempt))
            attempt += 1

    async def _dispatch(self, frame: dict[str, Any]) -> None:
        try:
            await self.handler(frame)
        except Exception:  # noqa: BLE001 - one bad frame must not kill the loop
            logger.exception("Socket frame handler raised")

    def _next_delay(self, attempt: int) -> float:
        exponential = self.base_backoff * (2**attempt)
        jitter = self._rng.uniform(0.0, exponential * 0.3) if exponential else 0.0
        return min(self.max_backoff, exponential + jitter)


def extract_events_frame(frame: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the actionable event out of a Slack Socket Mode frame.

    A Socket Mode ``events_api`` frame looks like::

        {"type": "events_api", "payload": {"type": "event_callback", "event": {...}}}

    Returns the ``event`` dict, or ``None`` for non-event frames (hello / ack)
    that should be ignored.
    """
    if not isinstance(frame, dict) or frame.get("type") != "events_api":
        return None
    payload = frame.get("payload")
    event = payload.get("event") if isinstance(payload, dict) else None
    return event if isinstance(event, dict) else None


def event_to_connector_message(event: dict[str, Any]) -> ConnectorMessage | None:
    """Translate a Slack event into :class:`ConnectorMessage`.

    Mirrors the webhook inbox path: handles user ``message`` events with text.
    Bot / thread-update / non-text events return ``None``.
    """
    if not isinstance(event, dict) or event.get("type") != "message":
        return None
    text = event.get("text")
    if not isinstance(text, str) or not text:
        return None
    if event.get("bot_id") is not None or event.get("subtype") in ("bot_message", "message_changed"):
        return None
    return ConnectorMessage(
        text=text,
        target={"channel": event.get("channel") or ""},
        metadata={"sender": event.get("user"), "source": "socket"},
    )


async def dispatch_socket_frame(
    handler: Callable[[ConnectorMessage], Awaitable[None]],
    frame: dict[str, Any],
) -> None:
    """Route a socket frame to ``handler`` (the channel's on_message callback)."""
    event = extract_events_frame(frame)
    if event is None:
        return
    message = event_to_connector_message(event)
    if message is None:
        return
    await handler(message)


__all__ = [
    "ReconnectLoop",
    "SlackSDKSocket",
    "SocketTransport",
    "dispatch_socket_frame",
    "event_to_connector_message",
    "extract_events_frame",
    "start_socket_mode",
]

class SlackSDKSocket:
    """Production :class:`SocketTransport` backed by ``slack_sdk.socket_mode``.

    The SDK client drives its own ``apps.connections.open`` WebSocket; we bridge
    its callback style into the stream-based :class:`SocketTransport` seam by
    pushing each envelope onto a JSON queue and exposing ``recv()`` over it.
    Real network — unit tests use a fake transport instead.
    """

    def __init__(self, app_token: str, bot_token: str, *, timeout: float = 10.0) -> None:
        from slack_sdk import WebClient
        from slack_sdk.socket_mode import SocketModeClient

        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        client = WebClient(token=bot_token, timeout=timeout)
        self._client = SocketModeClient(app_token=app_token, web_client=client)
        self._client.socket_mode_request_listeners.append(self._on_envelope)
        self._buffer: dict[str, Any] | None = None
        self._closed = False

    def _on_envelope(self, ctx) -> None:  # noqa: ANN001 - slack-sdk listener signature
        payload = getattr(ctx, "payload", None) if ctx is not None else None
        if isinstance(payload, dict):
            self._queue.put_nowait(payload)

    async def connect(self) -> None:
        await asyncio.to_thread(self._client.connect)

    async def recv(self) -> dict[str, Any] | None:
        """Block for the next envelope; return None once closed."""
        item = await self._queue.get()
        return None if item is _CLOSE_SENTINEL else item

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._queue.put(_CLOSE_SENTINEL)
            try:
                await asyncio.to_thread(self._client.disconnect)
            except Exception:  # pragma: no cover - best-effort
                pass


async def start_socket_mode(
    app_token: str,
    bot_token: str,
    on_message: Callable[[ConnectorMessage], Awaitable[None]],
    *,
    base_backoff: float = 0.5,
    max_backoff: float = 30.0,
) -> ReconnectLoop:
    """Open an outbound Slack Socket Mode WebSocket and dispatch messages.

    Returns the :class:`ReconnectLoop` (call ``await loop.stop()`` to close).
    """
    transport = SlackSDKSocket(app_token=app_token, bot_token=bot_token)
    loop = ReconnectLoop(
        transport,
        handler=lambda frame: dispatch_socket_frame(on_message, frame),
        base_backoff=base_backoff,
        max_backoff=max_backoff,
        sleep=asyncio.sleep,
    )
    return loop
