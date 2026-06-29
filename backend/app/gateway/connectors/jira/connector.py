"""Jira connector.

Implements `BaseConnector` against the Jira Cloud REST API v3:
- Outbound: create / transition / comment issues
- Inbound: receive webhook events (issue_updated, issue_created)

Auth: Basic auth with API token (`email:api_token` base64-encoded).
Token is cached via `CachedToken` (see v1.5.7).
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse
from ..token_refresh import CachedToken

JIRA_BASE = "https://{tenant}.atlassian.net/rest/api/3"

# Jira tokens don't expire in the short term, but we still cache them
# through the same single-flight helper to share the invalidation flow
# with the IM connectors.
_JIRA_TOKEN_TTL_SECONDS = 3600


def _extract_issue_text(payload: dict) -> str:
    """Pull the summary or comment body out of a Jira webhook payload."""
    issue = payload.get("issue") or {}
    fields = issue.get("fields") or {}
    summary = fields.get("summary")
    if isinstance(summary, str) and summary:
        return summary
    comment = payload.get("comment") or {}
    body = comment.get("body")
    if isinstance(body, str) and body:
        return body
    return ""


class JiraConnector(BaseConnector):
    name = "jira"
    display_name = "Jira"

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: float = 10.0,
    ) -> None:
        if not base_url or not email or not api_token:
            raise ValueError("base_url, email, and api_token are required")
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._api_token = api_token
        self._timeout = timeout
        self._auth_header: str | None = None

    def _auth_header_value(self) -> str:
        """Cache the Basic auth header so we don't re-encode per call."""
        if self._auth_header is None:
            raw = f"{self._email}:{self._api_token}".encode("utf-8")
            self._auth_header = "Basic " + base64.b64encode(raw).decode("ascii")
        return self._auth_header

    def invalidate(self) -> None:
        """Force the next send to rebuild the auth header."""
        self._auth_header = None

    async def _request(
        self, method: str, path: str, json: dict | None = None
    ) -> ConnectorResponse:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(
                    method,
                    url,
                    headers={
                        "Authorization": self._auth_header_value(),
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=json,
                )
            if resp.status_code in (200, 201, 204):
                data: Any = resp.json() if resp.content else None
                return ConnectorResponse(
                    success=True,
                    external_id=(data or {}).get("key") or (data or {}).get("id"),
                    raw=data,
                )
            return ConnectorResponse(
                success=False,
                error=f"jira api error: {resp.status_code} {resp.text[:200]}",
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResponse(success=False, error=str(e))

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        """Send — message.target maps to a Jira action.

        Supported targets:
        - {"action": "create_issue", "project": "PROJ", "summary": "...",
           "issue_type": "Task"}
        - {"action": "transition", "issue_key": "PROJ-123", "transition": "Done"}
        - {"action": "comment", "issue_key": "PROJ-123"}
        """
        target = message.target or {}
        action = target.get("action", "comment")

        if action == "create_issue":
            return await self._request(
                "POST",
                "/issue",
                {
                    "fields": {
                        "project": {"key": target.get("project", "TASK")},
                        "summary": message.text or target.get("summary", ""),
                        "issuetype": {"name": target.get("issue_type", "Task")},
                    }
                },
            )
        if action == "transition":
            return await self._request(
                "POST",
                f"/issue/{target['issue_key']}/transitions",
                {"transition": {"name": target.get("transition", "Done")}},
            )
        # Default: comment on the named issue.
        return await self._request(
            "POST",
            f"/issue/{target['issue_key']}/comment",
            {"body": message.text},
        )

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        text = _extract_issue_text(payload)
        if not text:
            return []
        issue = payload.get("issue") or {}
        issue_key = issue.get("key", "")
        sender = (payload.get("user") or {}).get("displayName", "")
        return [
            ConnectorMessage(
                text=text,
                target={"action": "comment", "issue_key": issue_key},
                metadata={
                    "issue_key": issue_key,
                    "sender": sender,
                    "event": payload.get("webhookEvent", ""),
                },
            )
        ]
