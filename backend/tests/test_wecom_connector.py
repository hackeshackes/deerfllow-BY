"""Tests for the WeCom (企业微信) connector."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.wecom.connector import WECOM_BASE, WeComConnector


@pytest.fixture
def connector():
    return WeComConnector(bot_id="bid", bot_secret="bsec")


@respx.mock
@pytest.mark.asyncio
async def test_wecom_send(connector):
    respx.get(f"{WECOM_BASE}/gettoken").mock(
        return_value=Response(
            200, json={"errcode": 0, "errmsg": "ok", "access_token": "at-1", "expires_in": 7200}
        )
    )
    respx.post(f"{WECOM_BASE}/message/send").mock(
        return_value=Response(200, json={"errcode": 0, "errmsg": "ok"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"user_id": "u-1"})
    )
    assert resp.success is True


@respx.mock
@pytest.mark.asyncio
async def test_wecom_send_failure(connector):
    respx.get(f"{WECOM_BASE}/gettoken").mock(
        return_value=Response(200, json={"access_token": "at-1", "expires_in": 7200})
    )
    respx.post(f"{WECOM_BASE}/message/send").mock(
        return_value=Response(200, json={"errcode": 40001, "errmsg": "invalid credential"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"user_id": "u-1"})
    )
    assert resp.success is False
    assert "invalid credential" in (resp.error or "")


@respx.mock
@pytest.mark.asyncio
async def test_wecom_token_cached(connector):
    token_route = respx.get(f"{WECOM_BASE}/gettoken").mock(
        return_value=Response(200, json={"access_token": "at-1", "expires_in": 7200})
    )
    respx.post(f"{WECOM_BASE}/message/send").mock(
        return_value=Response(200, json={"errcode": 0, "errmsg": "ok"})
    )
    await connector.send(ConnectorMessage(text="a", target={"user_id": "u-1"}))
    await connector.send(ConnectorMessage(text="b", target={"user_id": "u-1"}))
    assert token_route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_wecom_token_fetch_error(connector):
    respx.get(f"{WECOM_BASE}/gettoken").mock(
        return_value=Response(200, json={"errcode": 40013, "errmsg": "invalid corpid"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"user_id": "u-1"})
    )
    assert resp.success is False


@pytest.mark.asyncio
async def test_wecom_webhook_text_message():
    c = WeComConnector(bot_id="b", bot_secret="s")
    msgs = await c.receive_webhook(
        {
            "Content": "hi wecom",
            "FromUserName": "user-42",
        }
    )
    assert len(msgs) == 1
    assert msgs[0].text == "hi wecom"
    assert msgs[0].target == {"user_id": "user-42"}


@pytest.mark.asyncio
async def test_wecom_webhook_no_text_returns_empty():
    c = WeComConnector(bot_id="b", bot_secret="s")
    msgs = await c.receive_webhook({"FromUserName": "u"})
    assert msgs == []


@pytest.mark.asyncio
async def test_wecom_send_requires_user_id(connector):
    resp = await connector.send(ConnectorMessage(text="hi", target={}))
    assert resp.success is False
    assert "user_id" in (resp.error or "")
