"""Tests for the connector runtime — execution, retry, DLQ wiring."""
from __future__ import annotations

import pytest

from app.gateway.connectors.base import BaseConnector, ConnectorMessage, ConnectorResponse
from app.gateway.connectors.runtime import ConnectorRuntime


class OkConn(BaseConnector):
    name = "ok"
    display_name = "Ok"

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:  # type: ignore[override]
        return ConnectorResponse(success=True, external_id="e1")

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:  # type: ignore[override]
        return []


class FailConn(BaseConnector):
    name = "fail"
    display_name = "Fail"

    def __init__(self, fail_times: int = 10**6) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:  # type: ignore[override]
        self.calls += 1
        if self.calls <= self.fail_times:
            return ConnectorResponse(success=False, error="down")
        return ConnectorResponse(success=True, external_id="late-ok")

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:  # type: ignore[override]
        return []


class ExplodeConn(BaseConnector):
    name = "boom"
    display_name = "Boom"

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:  # type: ignore[override]
        raise RuntimeError("kaboom")

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:  # type: ignore[override]
        return []


@pytest.mark.asyncio
async def test_runtime_sends_successful_message():
    rt = ConnectorRuntime(retry_delay=0)
    rt.register(OkConn())
    resp = await rt.send("ok", ConnectorMessage(text="hi"))
    assert resp.success is True
    assert resp.external_id == "e1"
    assert resp.attempts == 1


@pytest.mark.asyncio
async def test_runtime_retries_on_failure_then_succeeds():
    conn = FailConn(fail_times=2)
    rt = ConnectorRuntime(max_retries=3, retry_delay=0)
    rt.register(conn)
    resp = await rt.send("fail", ConnectorMessage(text="hi"))
    assert resp.success is True
    assert resp.attempts == 3  # failed twice, succeeded on 3rd
    assert conn.calls == 3


@pytest.mark.asyncio
async def test_runtime_routes_to_dlq_after_max_retries():
    rt = ConnectorRuntime(max_retries=2, retry_delay=0, dlq_enabled=True)
    rt.register(FailConn(fail_times=10**6))
    resp = await rt.send("fail", ConnectorMessage(text="hi"))
    assert resp.success is False
    assert resp.attempts == 3  # 1 initial + 2 retries
    assert resp.dlq is not None
    assert resp.dlq.connector == "fail"
    assert resp.dlq.attempts == 3
    assert "down" in (resp.dlq.last_error or "")


@pytest.mark.asyncio
async def test_runtime_dlq_can_be_disabled():
    rt = ConnectorRuntime(max_retries=1, retry_delay=0, dlq_enabled=False)
    rt.register(FailConn(fail_times=10**6))
    resp = await rt.send("fail", ConnectorMessage(text="hi"))
    assert resp.success is False
    assert resp.dlq is None


@pytest.mark.asyncio
async def test_runtime_handles_exception_as_failure():
    rt = ConnectorRuntime(max_retries=1, retry_delay=0)
    rt.register(ExplodeConn())
    resp = await rt.send("boom", ConnectorMessage(text="hi"))
    assert resp.success is False
    assert resp.attempts == 2  # raised both times
    assert "kaboom" in (resp.error or "")


@pytest.mark.asyncio
async def test_runtime_unknown_connector_returns_error():
    rt = ConnectorRuntime()
    resp = await rt.send("nonexistent", ConnectorMessage(text="hi"))
    assert resp.success is False
    assert "unknown connector" in (resp.error or "").lower()
    assert resp.attempts == 0


@pytest.mark.asyncio
async def test_runtime_collects_all_dlq_entries():
    rt = ConnectorRuntime(max_retries=1, retry_delay=0, dlq_enabled=True)
    rt.register(FailConn(fail_times=10**6))
    await rt.send("fail", ConnectorMessage(text="a"))
    await rt.send("fail", ConnectorMessage(text="b"))
    assert len(rt.get_dlq()) == 2


@pytest.mark.asyncio
async def test_runtime_clear_dlq_returns_count():
    rt = ConnectorRuntime(max_retries=0, retry_delay=0)
    rt.register(FailConn(fail_times=10**6))
    await rt.send("fail", ConnectorMessage(text="x"))
    n = rt.clear_dlq()
    assert n == 1
    assert rt.get_dlq() == []
