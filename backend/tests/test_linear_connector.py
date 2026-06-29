"""Tests for the Linear connector."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.linear.connector import LinearConnector, LINEAR_GRAPHQL

TEAM_ID = "team-uuid-1"


@pytest.fixture
def connector():
    return LinearConnector(api_token="lin_api_xxx", team_id=TEAM_ID)


@respx.mock
@pytest.mark.asyncio
async def test_linear_create_issue(connector):
    respx.post(LINEAR_GRAPHQL).mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "id": "iss-1",
                            "identifier": "OPS-1",
                            "url": "https://linear.app/acme/issue/OPS-1",
                            "title": "Deploy v1.5.5",
                        },
                    }
                }
            },
        )
    )
    resp = await connector.send(
        ConnectorMessage(
            text="Deploy v1.5.5",
            target={"action": "create_issue", "team_id": TEAM_ID},
        )
    )
    assert resp.success is True


@respx.mock
@pytest.mark.asyncio
async def test_linear_create_issue_uses_default_team_id(connector):
    respx.post(LINEAR_GRAPHQL).mock(
        return_value=Response(
            200, json={"data": {"issueCreate": {"success": True, "issue": {"id": "x"}}}}
        )
    )
    resp = await connector.send(
        ConnectorMessage(text="t", target={"action": "create_issue"})
    )
    assert resp.success is True
    # Confirm the request body used the configured team_id
    body = respx.calls[0].request.content.decode()
    assert TEAM_ID in body


@respx.mock
@pytest.mark.asyncio
async def test_linear_comment(connector):
    respx.post(LINEAR_GRAPHQL).mock(
        return_value=Response(
            200,
            json={"data": {"commentCreate": {"success": True, "comment": {"id": "c-1"}}}},
        )
    )
    resp = await connector.send(
        ConnectorMessage(text="LGTM", target={"action": "comment", "issue_id": "iss-1"})
    )
    assert resp.success is True


@respx.mock
@pytest.mark.asyncio
async def test_linear_graphql_error_returns_failure(connector):
    respx.post(LINEAR_GRAPHQL).mock(
        return_value=Response(200, json={"errors": [{"message": "team not found"}]})
    )
    resp = await connector.send(
        ConnectorMessage(text="x", target={"action": "create_issue"})
    )
    assert resp.success is False
    assert "team not found" in resp.error


def test_linear_webhook_extracts_title():
    c = LinearConnector(api_token="x", team_id=TEAM_ID)
    import asyncio
    msgs = asyncio.run(
        c.receive_webhook(
            {
                "action": "create",
                "type": "Issue",
                "data": {
                    "issue": {"id": "iss-1", "title": "New bug"},
                    "actor": {"name": "Alice"},
                },
            }
        )
    )
    assert len(msgs) == 1
    assert msgs[0].text == "New bug"
    assert msgs[0].target["issue_id"] == "iss-1"


def test_linear_webhook_extracts_comment_body():
    c = LinearConnector(api_token="x", team_id=TEAM_ID)
    import asyncio
    msgs = asyncio.run(
        c.receive_webhook(
            {
                "action": "create",
                "type": "Comment",
                "data": {
                    "issue": {"id": "iss-1"},
                    "comment": {"body": "Looks good"},
                },
            }
        )
    )
    assert msgs[0].text == "Looks good"


def test_linear_webhook_no_text_returns_empty():
    c = LinearConnector(api_token="x", team_id=TEAM_ID)
    import asyncio
    msgs = asyncio.run(c.receive_webhook({"data": {"issue": {"id": "x"}}}))
    assert msgs == []


def test_linear_constructor_validates_inputs():
    with pytest.raises(ValueError, match="api_token and team_id"):
        LinearConnector(api_token="", team_id=TEAM_ID)
    with pytest.raises(ValueError, match="api_token and team_id"):
        LinearConnector(api_token="x", team_id="")
