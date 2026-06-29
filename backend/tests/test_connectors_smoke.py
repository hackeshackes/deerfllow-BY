"""End-to-end smoke for the connectors subsystem.

Composes: BaseConnector → ConnectorRegistry → ConnectorRuntime → WebhookBridge → InMemoryDLQStore.
Verifies the wiring holds together the way the admin API and integration tests
will exercise it.
"""
from __future__ import annotations

import pytest

from app.gateway.connectors.base import BaseConnector, ConnectorMessage, ConnectorResponse
from app.gateway.connectors.dlq import InMemoryDLQStore
from app.gateway.connectors.registry import ConnectorRegistry
from app.gateway.connectors.runtime import ConnectorRuntime
from app.gateway.connectors.webhook import WebhookBridge


class StubConn(BaseConnector):
    name = "stub"
    display_name = "Stub"

    def __init__(self, send_should_succeed: bool = True) -> None:
        self.send_should_succeed = send_should_succeed
        self.sent: list[ConnectorMessage] = []
        self.webhook_log: list[dict] = []

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:  # type: ignore[override]
        self.sent.append(message)
        if self.send_should_succeed:
            return ConnectorResponse(success=True, external_id="ok-1")
        return ConnectorResponse(success=False, error="stub down")

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:  # type: ignore[override]
        self.webhook_log.append(payload)
        text = payload.get("text", "")
        return [ConnectorMessage(text=text, target={"chat_id": payload.get("chat_id", "x")})]


def test_registry_registers_and_runtime_dispatches():
    reg = ConnectorRegistry()
    rt = ConnectorRuntime(retry_delay=0, dlq_enabled=True)
    conn = StubConn()
    reg.register(conn)
    rt.register(conn)
    assert reg.get("stub") is conn
    assert "stub" in rt._connectors  # internal — runtime keeps its own map


@pytest.mark.asyncio
async def test_end_to_end_success_through_runtime():
    rt = ConnectorRuntime(retry_delay=0)
    conn = StubConn()
    rt.register(conn)
    resp = await rt.send("stub", ConnectorMessage(text="hi"))
    assert resp.success is True
    assert resp.external_id == "ok-1"
    assert len(conn.sent) == 1


@pytest.mark.asyncio
async def test_dlq_round_trip_through_store():
    rt = ConnectorRuntime(max_retries=0, retry_delay=0, dlq_enabled=True)
    store = InMemoryDLQStore()
    rt.register(StubConn(send_should_succeed=False))
    resp = await rt.send("stub", ConnectorMessage(text="x"))
    assert resp.success is False
    assert resp.dlq is not None
    # Simulate what the admin endpoint does: persist the entry, then re-read.
    item_id = store.push(
        {
            "connector": resp.dlq.connector,
            "error": resp.dlq.last_error,
            "attempts": resp.dlq.attempts,
            "message": {"text": resp.dlq.message.text, "target": resp.dlq.message.target},
        }
    )
    fetched = store.get(item_id)
    assert fetched is not None
    assert fetched["connector"] == "stub"
    assert fetched["attempts"] == 1
    assert store.delete(item_id) is True


@pytest.mark.asyncio
async def test_webhook_bridge_handles_inbound_for_registered_connector():
    bridge = WebhookBridge()
    conn = StubConn()
    bridge.register(connector=conn, secret="shared-secret")
    msgs = await bridge.handle_inbound(
        "stub", secret="shared-secret", payload={"text": "hello", "chat_id": "c1"}
    )
    assert len(msgs) == 1
    assert msgs[0].text == "hello"
    assert conn.webhook_log == [{"text": "hello", "chat_id": "c1"}]


@pytest.mark.asyncio
async def test_unknown_connector_fails_through_runtime():
    rt = ConnectorRuntime()
    resp = await rt.send("nope", ConnectorMessage(text="x"))
    assert resp.success is False
    assert "unknown connector" in (resp.error or "").lower()
