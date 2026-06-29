"""Tests for the Feishu connector."""
from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.feishu.connector import (
    FEISHU_BASE,
    FeishuConnector,
    _extract_message_text,
)


@pytest.fixture
def connector():
    return FeishuConnector(app_id="cli_test", app_secret="sec_test")


def _token_mock():
    return respx.post(f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal").mock(
        return_value=Response(
            200, json={"code": 0, "msg": "ok", "tenant_access_token": "tok-1", "expire": 7200}
        )
    )


@respx.mock
@pytest.mark.asyncio
async def test_feishu_send_message_to_chat(connector):
    _token_mock()
    respx.post(f"{FEISHU_BASE}/im/v1/messages").mock(
        return_value=Response(
            200,
            json={
                "code": 0,
                "msg": "success",
                "data": {"message_id": "om-1"},
            },
        )
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "oc_x"})
    )
    assert resp.success is True
    assert resp.external_id == "om-1"


@respx.mock
@pytest.mark.asyncio
async def test_feishu_send_message_to_user(connector):
    _token_mock()
    route = respx.post(f"{FEISHU_BASE}/im/v1/messages").mock(
        return_value=Response(
            200, json={"code": 0, "data": {"message_id": "om-2"}}
        )
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"user_id": "ou_abc"})
    )
    assert resp.success is True
    assert route.called
    # Verify receive_id_type is open_id when sending to a user
    request = route.calls[0].request
    assert "receive_id_type=open_id" in str(request.url)


@respx.mock
@pytest.mark.asyncio
async def test_feishu_send_api_error_returns_failure(connector):
    _token_mock()
    respx.post(f"{FEISHU_BASE}/im/v1/messages").mock(
        return_value=Response(200, json={"code": 230020, "msg": "permission denied"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "oc_x"})
    )
    assert resp.success is False
    assert "permission" in (resp.error or "").lower()


@respx.mock
@pytest.mark.asyncio
async def test_feishu_send_token_error(connector):
    """If the token endpoint itself fails, send should fail rather than hang."""
    respx.post(f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal").mock(
        return_value=Response(200, json={"code": 10003, "msg": "invalid app_secret"})
    )
    resp = await connector.send(
        ConnectorMessage(text="hi", target={"chat_id": "oc_x"})
    )
    assert resp.success is False


@respx.mock
@pytest.mark.asyncio
async def test_feishu_send_token_cached(connector):
    """Second call should reuse the cached token, not re-fetch."""
    token_route = _token_mock()
    respx.post(f"{FEISHU_BASE}/im/v1/messages").mock(
        return_value=Response(200, json={"code": 0, "data": {"message_id": "om-3"}})
    )
    await connector.send(ConnectorMessage(text="a", target={"chat_id": "c1"}))
    await connector.send(ConnectorMessage(text="b", target={"chat_id": "c1"}))
    # Token endpoint called exactly once across two sends.
    assert token_route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_feishu_token_cache_ttl_is_5400s(connector):
    """Feishu tokens last 2h; we refresh at 5400s (15min early).

    Verified by triggering a token fetch and inspecting the cache's
    remaining TTL. A regression here would either blow the upstream
    rate limit (too aggressive) or produce 401s (too lazy).
    """
    import time
    _token_mock()
    respx.post(f"{FEISHU_BASE}/im/v1/messages").mock(
        return_value=Response(200, json={"code": 0, "data": {"message_id": "om-ttl"}})
    )
    await connector.send(ConnectorMessage(text="x", target={"chat_id": "c1"}))

    assert connector._token_cache is not None  # noqa: SLF001
    remaining = connector._token_cache._expires_at - time.monotonic()  # noqa: SLF001
    assert 5300 <= remaining <= 5400

@pytest.mark.asyncio
async def test_feishu_webhook_url_verification_returns_empty():
    c = FeishuConnector(app_id="x", app_secret="y")
    msgs = await c.receive_webhook(
        {"type": "url_verification", "challenge": "abc-123"}
    )
    assert msgs == []


@pytest.mark.asyncio
async def test_feishu_webhook_message_event():
    c = FeishuConnector(app_id="x", app_secret="y")
    payload = {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_abc"}},
            "message": {
                "message_id": "om_evt_1",
                "chat_id": "oc_evt",
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps({"text": "hi from feishu"}),
            },
        },
    }
    msgs = await c.receive_webhook(payload)
    assert len(msgs) == 1
    assert msgs[0].text == "hi from feishu"
    assert msgs[0].target == {"chat_id": "oc_evt"}
    assert msgs[0].metadata["sender"] == "ou_abc"


@pytest.mark.asyncio
async def test_feishu_webhook_non_text_message_returns_empty():
    c = FeishuConnector(app_id="x", app_secret="y")
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_evt",
                "message_type": "image",
                "content": json.dumps({"image_key": "img-1"}),
            }
        }
    }
    msgs = await c.receive_webhook(payload)
    assert msgs == []


def test_extract_message_text_handles_dict_content():
    content = json.dumps({"text": "hello"})
    assert _extract_message_text({"content": content}) == "hello"


def test_extract_message_text_handles_missing_content():
    assert _extract_message_text({}) == ""
    assert _extract_message_text({"content": "not-json"}) == ""
