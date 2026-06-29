"""Tests for the inbound webhook bridge."""
from __future__ import annotations

import pytest

from app.gateway.connectors.base import BaseConnector, ConnectorMessage, ConnectorResponse
from app.gateway.connectors.webhook import WebhookBridge


class FakeConn(BaseConnector):
    name = "fake"
    display_name = "Fake"

    def __init__(self) -> None:
        self.received: list[dict] = []

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:  # type: ignore[override]
        return ConnectorResponse(success=True)

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:  # type: ignore[override]
        self.received.append(payload)
        return [
            ConnectorMessage(
                text=payload.get("text", ""),
                target={"chat_id": payload.get("chat_id")},
            )
        ]


@pytest.mark.asyncio
async def test_bridge_inbound_returns_messages():
    bridge = WebhookBridge()
    conn = FakeConn()
    bridge.register(connector=conn, secret="s1")
    messages = await bridge.handle_inbound(
        "fake", secret="s1", payload={"text": "hello", "chat_id": "c1"}
    )
    assert len(messages) == 1
    assert messages[0].text == "hello"
    assert messages[0].target == {"chat_id": "c1"}
    assert conn.received == [{"text": "hello", "chat_id": "c1"}]


@pytest.mark.asyncio
async def test_bridge_rejects_wrong_secret():
    bridge = WebhookBridge()
    bridge.register(connector=FakeConn(), secret="s1")
    with pytest.raises(PermissionError, match="invalid webhook secret"):
        await bridge.handle_inbound("fake", secret="wrong", payload={})


@pytest.mark.asyncio
async def test_bridge_rejects_unknown_connector():
    bridge = WebhookBridge()
    with pytest.raises(KeyError, match="not registered"):
        await bridge.handle_inbound("unknown", secret="s", payload={})


@pytest.mark.asyncio
async def test_bridge_unregister_removes_route():
    bridge = WebhookBridge()
    bridge.register(connector=FakeConn(), secret="s1")
    bridge.unregister("fake")
    with pytest.raises(KeyError):
        await bridge.handle_inbound("fake", secret="s1", payload={})


@pytest.mark.asyncio
async def test_bridge_empty_messages_is_valid():
    """A connector may legitimately return [] (e.g. URL verification challenges)."""

    class SilentConn(BaseConnector):
        name = "silent"

        async def send(self, message):  # type: ignore[override]
            return ConnectorResponse(success=True)

        async def receive_webhook(self, payload):  # type: ignore[override]
            return []

    bridge = WebhookBridge()
    bridge.register(connector=SilentConn(), secret="x")
    msgs = await bridge.handle_inbound("silent", secret="x", payload={"challenge": "abc"})
    assert msgs == []


@pytest.mark.asyncio
async def test_bridge_register_replaces_existing():
    bridge = WebhookBridge()
    bridge.register(connector=FakeConn(), secret="old")
    bridge.register(connector=FakeConn(), secret="new")
    with pytest.raises(PermissionError):
        await bridge.handle_inbound("fake", secret="old", payload={})
    # New secret works
    msgs = await bridge.handle_inbound("fake", secret="new", payload={"text": "hi"})
    assert msgs[0].text == "hi"
