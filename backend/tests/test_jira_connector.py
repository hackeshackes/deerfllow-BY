"""Tests for the Jira connector."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.jira.connector import JiraConnector

BASE = "https://acme.atlassian.net/rest/api/3"


@pytest.fixture
def connector():
    return JiraConnector(
        base_url=BASE,
        email="bot@acme.com",
        api_token="tok-1",
    )


@respx.mock
@pytest.mark.asyncio
async def test_jira_create_issue(connector):
    respx.post(f"{BASE}/issue").mock(
        return_value=Response(
            201, json={"id": "10001", "key": "OPS-42"}
        )
    )
    resp = await connector.send(
        ConnectorMessage(
            text="Deploy v1.5.5",
            target={"action": "create_issue", "project": "OPS", "issue_type": "Task"},
        )
    )
    assert resp.success is True
    assert resp.external_id == "OPS-42"


@respx.mock
@pytest.mark.asyncio
async def test_jira_transition(connector):
    route = respx.post(f"{BASE}/issue/OPS-42/transitions").mock(
        return_value=Response(204)
    )
    resp = await connector.send(
        ConnectorMessage(
            text="",
            target={"action": "transition", "issue_key": "OPS-42", "transition": "Done"},
        )
    )
    assert resp.success is True
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_jira_comment(connector):
    respx.post(f"{BASE}/issue/OPS-42/comment").mock(
        return_value=Response(201, json={"id": "c-1"})
    )
    resp = await connector.send(
        ConnectorMessage(text="LGTM", target={"action": "comment", "issue_key": "OPS-42"})
    )
    assert resp.success is True


@respx.mock
@pytest.mark.asyncio
async def test_jira_failure(connector):
    respx.post(f"{BASE}/issue").mock(
        return_value=Response(401, text="Unauthorized")
    )
    resp = await connector.send(
        ConnectorMessage(text="x", target={"action": "create_issue"})
    )
    assert resp.success is False
    assert "401" in resp.error


def test_jira_invalidate_rebuilds_auth_header(connector):
    connector._auth_header = "stale"
    connector.invalidate()
    assert connector._auth_header is None
    h1 = connector._auth_header_value()
    h2 = connector._auth_header_value()
    # Subsequent calls reuse the cached header (no rebuild)
    assert h1 == h2


def test_jira_webhook_extracts_summary():
    c = JiraConnector(base_url=BASE, email="x", api_token="y")
    import asyncio
    msgs = asyncio.run(
        c.receive_webhook(
            {
                "webhookEvent": "jira:issue_created",
                "issue": {
                    "key": "OPS-42",
                    "fields": {"summary": "Deploy v1.5.5"},
                },
            }
        )
    )
    assert len(msgs) == 1
    assert msgs[0].text == "Deploy v1.5.5"
    assert msgs[0].target["issue_key"] == "OPS-42"
    assert msgs[0].metadata["event"] == "jira:issue_created"


def test_jira_webhook_falls_back_to_comment_body():
    c = JiraConnector(base_url=BASE, email="x", api_token="y")
    import asyncio
    msgs = asyncio.run(
        c.receive_webhook(
            {
                "webhookEvent": "comment_created",
                "issue": {"key": "OPS-1"},
                "comment": {"body": "Looks good"},
            }
        )
    )
    assert msgs[0].text == "Looks good"


def test_jira_webhook_no_text_returns_empty():
    c = JiraConnector(base_url=BASE, email="x", api_token="y")
    import asyncio
    msgs = asyncio.run(c.receive_webhook({"issue": {"key": "OPS-1"}}))
    assert msgs == []


def test_jira_constructor_validates_inputs():
    with pytest.raises(ValueError, match="base_url, email, and api_token"):
        JiraConnector(base_url="", email="x", api_token="y")
    with pytest.raises(ValueError, match="base_url, email, and api_token"):
        JiraConnector(base_url="x", email="", api_token="y")
    with pytest.raises(ValueError, match="base_url, email, and api_token"):
        JiraConnector(base_url="x", email="y", api_token="")
