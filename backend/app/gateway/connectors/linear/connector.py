"""Linear connector.

Implements `BaseConnector` against the Linear GraphQL API:
- Outbound: create issues, add comments via the GraphQL endpoint
- Inbound: receive webhook payloads (Linear uses HMAC-SHA256 signing;
  the verification is the gateway's job, this class just parses)

Auth: Personal API token sent in the `Authorization` header.
"""
from __future__ import annotations

from typing import Any

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse

LINEAR_GRAPHQL = "https://api.linear.app/graphql"

# Linear API tokens don't expire; we still hold the connector-level
# header in a class attribute so subclasses can add a refresh path later.
_LINEAR_TOKEN_TTL_SECONDS = 86400 * 30  # effectively infinite for the MVP


def _extract_issue_text(payload: dict) -> str:
    """Pull the issue title or comment body from a Linear webhook payload."""
    data = payload.get("data") or {}
    issue = data.get("issue") or payload.get("issue") or {}
    title = issue.get("title")
    if isinstance(title, str) and title:
        return title
    comment = data.get("comment") or payload.get("comment") or {}
    body = comment.get("body")
    if isinstance(body, str) and body:
        return body
    return ""


_CREATE_ISSUE_MUTATION = """
mutation MicXCreateIssue($title: String!, $teamId: String!, $description: String) {
  issueCreate(input: {title: $title, teamId: $teamId, description: $description}) {
    success
    issue { id identifier url title }
  }
}
""".strip()


_ADD_COMMENT_MUTATION = """
mutation MicXAddComment($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment { id body createdAt }
  }
}
""".strip()


class LinearConnector(BaseConnector):
    name = "linear"
    display_name = "Linear"

    def __init__(
        self,
        api_token: str,
        team_id: str,
        timeout: float = 10.0,
    ) -> None:
        if not api_token or not team_id:
            raise ValueError("api_token and team_id are required")
        self._api_token = api_token
        self._team_id = team_id
        self._timeout = timeout

    async def _graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> ConnectorResponse:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    LINEAR_GRAPHQL,
                    headers={
                        "Authorization": self._api_token,
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": variables or {}},
                )
            data = resp.json()
            if "errors" in data and data["errors"]:
                return ConnectorResponse(
                    success=False,
                    error=f"linear graphql error: {data['errors'][0].get('message')}",
                )
            return ConnectorResponse(success=True, raw=data.get("data"))
        except Exception as e:  # noqa: BLE001
            return ConnectorResponse(success=False, error=str(e))

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        target = message.target or {}
        action = target.get("action", "comment")

        if action == "create_issue":
            return await self._graphql(
                _CREATE_ISSUE_MUTATION,
                {
                    "title": message.text or target.get("title", ""),
                    "teamId": target.get("team_id", self._team_id),
                    "description": target.get("description", message.text),
                },
            )
        # default: comment
        return await self._graphql(
            _ADD_COMMENT_MUTATION,
            {
                "issueId": target["issue_id"],
                "body": message.text,
            },
        )

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        text = _extract_issue_text(payload)
        if not text:
            return []
        data = payload.get("data") or {}
        issue = data.get("issue") or payload.get("issue") or {}
        issue_id = issue.get("id", "")
        sender = (data.get("actor") or {}).get("name", "")
        return [
            ConnectorMessage(
                text=text,
                target={"action": "comment", "issue_id": issue_id},
                metadata={
                    "issue_id": issue_id,
                    "sender": sender,
                    "action": payload.get("action", ""),
                    "type": payload.get("type", ""),
                },
            )
        ]
