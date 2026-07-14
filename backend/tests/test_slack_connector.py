"""Tests for the Slack connector (v1.6.1, Task C3).

Slack connector surfaces used by the tests:

* ``send()``         — POST /chat.postMessage with bearer auth
* ``receive_webhook`` — maps Slack Event API ``event_callback`` → ``ConnectorMessage``
* ``verify_webhook_challenge`` — echo the URL-verification challenge back
* ``health_check``  — POST /auth.test
* registry integration via ``MICX_CONNECTORS``

Mocking strategy: ``respx`` (already in dev deps). Production uses
``httpx.AsyncClient`` with bearer auth against slack.com/api.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.integrations.builtin import register_builtin_connectors
from app.gateway.connectors.registry import ConnectorRegistry
from app.gateway.connectors.slack.connector import SlackConnector

# ---- Construction ----


def test_slack_connector_rejects_empty_token():
    with pytest.raises(ValueError, match="bot_token"):
        SlackConnector(bot_token="")


def test_slack_connector_name_and_display_name():
    connector = SlackConnector(bot_token="xoxb-test")
    assert connector.name == "slack"
    assert connector.display_name == "Slack"


# ---- Outbound: chat.postMessage ----


@pytest.mark.asyncio
async def test_slack_send_posts_to_chat_post_message():
    connector = SlackConnector(bot_token="xoxb-test")
    with respx.mock() as mock:
        route = mock.post("https://slack.com/api/chat.postMessage").mock(
            return_value=Response(
                200,
                json={"ok": True, "channel": "C123", "ts": "1234567890.123456"},
            )
        )
        result = await connector.send(
            ConnectorMessage(text="hi", target={"channel": "#general"})
        )
    assert result.success is True
    assert result.external_id == "1234567890.123456"
    # The body should have channel + text + Bearer auth
    assert route.called
    request = route.calls[0].request
    assert request.headers.get("Authorization") == "Bearer xoxb-test"
    import json

    payload = json.loads(request.content)
    assert payload["channel"] == "#general"
    assert payload["text"] == "hi"


@pytest.mark.asyncio
async def test_slack_send_returns_failure_when_api_returns_ok_false():
    connector = SlackConnector(bot_token="xoxb-test")
    with respx.mock() as mock:
        mock.post("https://slack.com/api/chat.postMessage").mock(
            return_value=Response(200, json={"ok": False, "error": "channel_not_found"})
        )
        result = await connector.send(
            ConnectorMessage(text="hi", target={"channel": "#missing"})
        )
    assert result.success is False
    assert "channel_not_found" in (result.error or "")


@pytest.mark.asyncio
async def test_slack_send_requires_channel_target():
    connector = SlackConnector(bot_token="xoxb-test")
    result = await connector.send(ConnectorMessage(text="hi", target={}))
    assert result.success is False
    assert "channel" in (result.error or "")


# ---- Inbound: event_callback ----


@pytest.mark.asyncio
async def test_slack_receive_webhook_maps_event_callback_to_message():
    connector = SlackConnector(bot_token="xoxb-test")
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "hello from slack",
            "channel": "C123",
            "user": "U456",
            "ts": "1700000000.000100",
        },
    }
    messages = await connector.receive_webhook(payload)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.text == "hello from slack"
    assert msg.target.get("channel") == "C123"
    assert msg.target.get("user_id") == "U456"
    assert msg.metadata.get("slack_event_type") == "message"
    assert msg.metadata.get("slack_event_ts") == "1700000000.000100"


@pytest.mark.asyncio
async def test_slack_receive_webhook_ignores_non_message_event_callback():
    connector = SlackConnector(bot_token="xoxb-test")
    # Reaction_added should NOT surface as a chat message — the runtime
    # only translates message-shaped events. We return [] so the bridge
    # does not emit a runnable.
    payload = {
        "type": "event_callback",
        "event": {"type": "reaction_added", "user": "U1", "reaction": "eyes"},
    }
    assert await connector.receive_webhook(payload) == []


@pytest.mark.asyncio
async def test_slack_receive_webhook_returns_empty_for_url_verification_event():
    """URL-verification is not a chat message; receive_webhook returns
    no messages and the bridge does NOT call verify_challenge on it —
    the bridge handler is responsible for that separate flow.
    """
    connector = SlackConnector(bot_token="xoxb-test")
    payload = {
        "type": "url_verification",
        "challenge": "abc123",
        "token": "ignored",
    }
    assert await connector.receive_webhook(payload) == []


# ---- URL verification (Slack Events API handshake) ----


def test_verify_challenge_echoes_prompt():
    connector = SlackConnector(bot_token="xoxb-test")
    challenge = connector.verify_challenge_event(
        {"type": "url_verification", "challenge": "abc123"}
    )
    assert challenge == "abc123"


def test_verify_challenge_returns_none_on_non_url_verification():
    connector = SlackConnector(bot_token="xoxb-test")
    # Even on a bug-bridge that misroutes a regular event, the helper
    # must not mistake it for a verification challenge.
    assert (
        connector.verify_challenge_event(
            {"type": "event_callback", "challenge": "abc123"}
        )
        is None
    )


# ---- Health check ----


@pytest.mark.asyncio
async def test_slack_health_check_calls_auth_test():
    connector = SlackConnector(bot_token="xoxb-test")
    with respx.mock() as mock:
        mock.post("https://slack.com/api/auth.test").mock(
            return_value=Response(200, json={"ok": True, "user": "bot", "user_id": "B1"})
        )
        assert await connector.health_check() is True


@pytest.mark.asyncio
async def test_slack_health_check_fails_on_auth_error():
    connector = SlackConnector(bot_token="xoxb-bad")
    with respx.mock() as mock:
        mock.post("https://slack.com/api/auth.test").mock(
            return_value=Response(200, json={"ok": False, "error": "invalid_auth"})
        )
        assert await connector.health_check() is False


# ---- Registry / MICX_CONNECTORS integration ----


def test_slack_builtin_registration_with_full_creds():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"slack": {"bot_token": "xoxb-x"}},
    )
    assert "slack" in reg.list_names()
    assert isinstance(reg.get("slack"), SlackConnector)


def test_slack_builtin_registration_skips_missing_token():
    reg = ConnectorRegistry()
    register_builtin_connectors(registry=reg, config={"slack": {}})
    assert "slack" not in reg.list_names()
