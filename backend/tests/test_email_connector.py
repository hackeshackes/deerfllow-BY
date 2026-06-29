"""Tests for the Email connector."""
from __future__ import annotations

import os
from email import message_from_bytes
from unittest.mock import AsyncMock, patch

import pytest

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.email.connector import EmailConnector


@pytest.fixture
def connector():
    return EmailConnector(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="u@x",
        smtp_password="p",
        imap_host="imap.example.com",
        imap_port=993,
        from_address="bot@x",
    )


def test_connector_name_and_display():
    c = EmailConnector(
        smtp_host="h", smtp_port=1, smtp_user="u", smtp_password="p",
        imap_host="h", imap_port=1, from_address="f",
    )
    assert c.name == "email"
    assert c.display_name == "Email (SMTP/IMAP)"


@pytest.mark.asyncio
async def test_email_send_calls_smtp(connector):
    with patch("app.gateway.connectors.email.connector.aiosmtplib") as mock_smtp:
        mock_smtp.send = AsyncMock(return_value=(250, "OK"))
        resp = await connector.send(
            ConnectorMessage(
                text="hi",
                target={"to": "user@example.com", "subject": "Hello"},
            )
        )
    assert resp.success is True
    mock_smtp.send.assert_called_once()
    call_args = mock_smtp.send.call_args
    msg = call_args[0][0]
    raw = msg.as_bytes() if hasattr(msg, "as_bytes") else bytes(msg)
    parsed = message_from_bytes(raw)
    assert parsed["From"] == "bot@x"
    assert parsed["To"] == "user@example.com"
    assert parsed["Subject"] == "Hello"
    assert b"hi" in raw


@pytest.mark.asyncio
async def test_email_send_failure(connector):
    with patch("app.gateway.connectors.email.connector.aiosmtplib") as mock_smtp:
        mock_smtp.send = AsyncMock(side_effect=Exception("smtp down"))
        resp = await connector.send(
            ConnectorMessage(
                text="x", target={"to": "u@x", "subject": "x"}
            )
        )
    assert resp.success is False
    assert "smtp down" in (resp.error or "")


@pytest.mark.asyncio
async def test_email_send_requires_to_target(connector):
    resp = await connector.send(ConnectorMessage(text="x", target={"subject": "x"}))
    assert resp.success is False
    assert "to" in (resp.error or "").lower()


@pytest.mark.asyncio
async def test_email_send_default_subject(connector):
    with patch("app.gateway.connectors.email.connector.aiosmtplib") as mock_smtp:
        mock_smtp.send = AsyncMock(return_value=(250, "OK"))
        resp = await connector.send(
            ConnectorMessage(text="body", target={"to": "u@x"})
        )
    assert resp.success is True
    raw = mock_smtp.send.call_args[0][0].as_bytes()
    parsed = message_from_bytes(raw)
    assert parsed["Subject"] == "(no subject)"


@pytest.mark.asyncio
async def test_email_webhook_returns_empty(connector):
    """Email has no traditional webhook — IMAP IDLE is handled by a poller."""
    msgs = await connector.receive_webhook({"anything": "goes"})
    assert msgs == []
