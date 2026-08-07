"""Tests for Slack Socket Mode reconnect + frame dispatch (v1.7 M5).

Exercises the transport-agnostic core against a fake WebSocket:
1. Frame extraction / event -> ConnectorMessage translation.
2. Reconnect loop: a dropped connection re-connects and frames are handled.
3. Non-text / bot / non-events frames are ignored.
"""

from __future__ import annotations

import random

import pytest

from app.gateway.connectors.slack.socket_mode import (
    ReconnectLoop,
    dispatch_socket_frame,
    event_to_connector_message,
    extract_events_frame,
)


def _events_frame(event: dict) -> dict:
    return {"type": "events_api", "payload": {"type": "event_callback", "event": event}}


# ---------------------------------------------------------------------------
# Frame extraction + translation
# ---------------------------------------------------------------------------


def test_extract_events_frame_returns_event():
    event = {"type": "message", "text": "hi", "channel": "C1", "user": "U1"}
    assert extract_events_frame(_events_frame(event)) == event


def test_extract_ignores_non_event_frame():
    assert extract_events_frame({"type": "hello", "payload": {}}) is None
    assert extract_events_frame({"type": "events_api", "payload": {}}) is None
    assert extract_events_frame({"type": "events_api"}) is None


def test_event_to_message():
    msg = event_to_connector_message(
        {"type": "message", "text": "hello", "channel": "C1", "user": "U1"}
    )
    assert msg is not None
    assert msg.text == "hello"
    assert msg.target == {"channel": "C1"}
    assert msg.metadata["sender"] == "U1"


def test_event_to_message_ignores_bot_and_notext():
    assert event_to_connector_message({"type": "message", "text": "x", "bot_id": "B1"}) is None
    assert event_to_connector_message({"type": "message", "text": ""}) is None
    assert event_to_connector_message({"type": "file_share", "text": "f"}) is None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_socket_frame_routes_message():
    received: list[str] = []

    async def handler(message) -> None:  # noqa: ANN001
        received.append(message.text)

    frame = _events_frame({"type": "message", "text": "ping", "channel": "C1", "user": "U1"})
    await dispatch_socket_frame(handler, frame)

    assert received == ["ping"]


@pytest.mark.asyncio
async def test_dispatch_ignores_hello_frame():
    called = False

    async def handler(message) -> None:  # noqa: ANN001
        nonlocal called
        called = True

    await dispatch_socket_frame(handler, {"type": "hello"})
    assert not called


# ---------------------------------------------------------------------------
# Reconnect loop
# ---------------------------------------------------------------------------


class _DroppingTransport:
    """Delivers a fixed list of frames, then reports a drop (recv → None)."""

    def __init__(self, frames: list[dict]) -> None:
        self.frames = list(frames)
        self.connect_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1

    async def recv(self) -> dict | None:
        if self.frames:
            return self.frames.pop(0)
        return None  # drop

    async def close(self) -> None:
        pass


async def _noop_sleep(_seconds: float) -> None:
    pass


async def _noop_handler(_frame: dict) -> None:
    pass


@pytest.mark.asyncio
async def test_reconnect_loop_dispatches_and_reattaches():
    """Frames are dispatched; after a drop the loop reconnects (bounded)."""
    transport = _DroppingTransport(
        [
            _events_frame({"type": "message", "text": "a", "channel": "C1", "user": "U1"}),
            _events_frame({"type": "message", "text": "b", "channel": "C1", "user": "U1"}),
        ]
    )
    handled: list[str] = []

    async def frame_handler(frame: dict) -> None:
        event = extract_events_frame(frame)
        if event:
            msg = event_to_connector_message(event)
            if msg:
                handled.append(msg.text)

    loop = ReconnectLoop(
        transport,
        frame_handler,
        base_backoff=0.0,
        max_attempts=3,  # bounded: run() returns on its own, no infinite spin
        rng=random.Random(1),
        sleep=_noop_sleep,
    )
    # run() self-terminates via max_attempts — no wait_for/timeout needed.
    await loop.run()

    assert handled == ["a", "b"]
    assert loop.reconnect_count >= 1


@pytest.mark.asyncio
async def test_reconnect_gives_up_after_max_attempts():
    # Empty transport: every recv drops immediately → loop hits max_attempts.
    transport = _DroppingTransport([])
    loop = ReconnectLoop(
        transport,
        handler=_noop_handler,
        base_backoff=0.0,
        max_attempts=2,
        sleep=_noop_sleep,
    )
    await loop.run()  # returns cleanly after bounded reconnects

    assert loop.reconnect_count == 2
    assert loop.stop_requested is False