"""Tests for the DingTalk connector."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.dingtalk.connector import DINGTALK_BASE, DingTalkConnector


@pytest.fixture
def connector():
    return DingTalkConnector(client_id="cid", client_secret="csec")


@respx.mock
@pytest.mark.asyncio
async def test_dingtalk_send_message(connector):
    respx.post(f"{DINGTALK_BASE}/v1.0/oauth2/accessToken").mock(
        return_value=Response(200, json={"accessToken": "at-1", "expireIn": 7200})
    )
    respx.post(f"{DINGTALK_BASE}/v1.0/robot/groupMessages/send").mock(
        return_value=Response(200, json={"processQueryKey": "pqk-1"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "cidxxx"})
    )
    assert resp.success is True
    assert resp.external_id == "pqk-1"


@respx.mock
@pytest.mark.asyncio
async def test_dingtalk_send_failure(connector):
    respx.post(f"{DINGTALK_BASE}/v1.0/oauth2/accessToken").mock(
        return_value=Response(200, json={"accessToken": "at-1", "expireIn": 7200})
    )
    respx.post(f"{DINGTALK_BASE}/v1.0/robot/groupMessages/send").mock(
        return_value=Response(200, json={"errcode": 43004, "errmsg": "chat not found"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "cidxxx"})
    )
    assert resp.success is False
    assert "chat not found" in (resp.error or "")


@respx.mock
@pytest.mark.asyncio
async def test_dingtalk_token_cached(connector):
    token_route = respx.post(f"{DINGTALK_BASE}/v1.0/oauth2/accessToken").mock(
        return_value=Response(200, json={"accessToken": "at-1", "expireIn": 7200})
    )
    respx.post(f"{DINGTALK_BASE}/v1.0/robot/groupMessages/send").mock(
        return_value=Response(200, json={"processQueryKey": "pqk"})
    )
    await connector.send(ConnectorMessage(text="a", target={"chat_id": "c1"}))
    await connector.send(ConnectorMessage(text="b", target={"chat_id": "c1"}))
    assert token_route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_dingtalk_token_error(connector):
    respx.post(f"{DINGTALK_BASE}/v1.0/oauth2/accessToken").mock(
        return_value=Response(200, json={"accessToken": ""})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "c1"})
    )
    assert resp.success is False


@pytest.mark.asyncio
async def test_dingtalk_webhook_message_returns_text():
    c = DingTalkConnector(client_id="cid", client_secret="sec")
    payload = {
        "conversationId": "conv-1",
        "senderId": "user-1",
        "text": {"content": "hello ding"},
    }
    msgs = await c.receive_webhook(payload)
    assert len(msgs) == 1
    assert msgs[0].text == "hello ding"
    assert msgs[0].target == {"chat_id": "conv-1"}
    assert msgs[0].metadata["sender"] == "user-1"


@pytest.mark.asyncio
async def test_dingtalk_webhook_empty_text_returns_empty():
    c = DingTalkConnector(client_id="cid", client_secret="sec")
    msgs = await c.receive_webhook({"text": {"content": ""}})
    assert msgs == []


@pytest.mark.asyncio
async def test_dingtalk_webhook_no_text_field_returns_empty():
    c = DingTalkConnector(client_id="cid", client_secret="sec")
    msgs = await c.receive_webhook({"conversationId": "c-1"})
    assert msgs == []
