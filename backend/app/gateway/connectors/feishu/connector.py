"""Feishu (Lark) connector.

Implements `BaseConnector` against the Feishu Open Platform:
- Outbound: send text message to a chat (oc_*) or user (ou_*)
- Inbound: receive event webhook payloads, including URL verification

The token is cached in-memory for the process lifetime; the OpenAPI TTL is
typically 2 hours, but for the MVP we don't refresh proactively — the next
send will surface an auth error and a higher-level reload will reset.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse

FEISHU_BASE = "https://open.feishu.cn/open-apis"


def _extract_message_text(event: dict) -> str:
    """Pull `text` out of a Feishu message event's `content` JSON string."""
    content = event.get("content")
    if not isinstance(content, str):
        return ""
    try:
        parsed = json.loads(content)
    except (TypeError, ValueError):
        return ""
    if isinstance(parsed, dict):
        text = parsed.get("text")
        if isinstance(text, str):
            return text
    return ""


class FeishuConnector(BaseConnector):
    name = "feishu"
    display_name = "Feishu (Lark)"

    def __init__(self, app_id: str, app_secret: str, timeout: float = 10.0) -> None:
        if not app_id or not app_secret:
            raise ValueError("app_id and app_secret are required")
        self._app_id = app_id
        self._app_secret = app_secret
        self._timeout = timeout
        self._token: str | None = None

    # --------------------------------------------------------------------- auth
    async def _get_token(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
                json={"app_id": self._app_id, "app_secret": self._app_secret},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(
                    f"feishu token error: code={data.get('code')} msg={data.get('msg')}"
                )
            self._token = data["tenant_access_token"]
            return self._token

    # -------------------------------------------------------------------- send
    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        try:
            token = await self._get_token()
            chat_id = message.target.get("chat_id")
            user_id = message.target.get("user_id")
            if chat_id:
                receive_id, receive_id_type = chat_id, "chat_id"
            elif user_id:
                receive_id, receive_id_type = user_id, "open_id"
            else:
                return ConnectorResponse(
                    success=False, error="feishu send requires chat_id or user_id"
                )

            content_text = message.text.replace("\\", "\\\\").replace('"', '\\"')
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{FEISHU_BASE}/im/v1/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": receive_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": message.text}),
                    },
                    params={"receive_id_type": receive_id_type},
                )
            data: dict[str, Any] = resp.json()
            if data.get("code") == 0:
                return ConnectorResponse(
                    success=True,
                    external_id=(data.get("data") or {}).get("message_id"),
                    raw=data,
                )
            return ConnectorResponse(
                success=False,
                error=f"feishu api error: code={data.get('code')} msg={data.get('msg')}",
                raw=data,
            )
        except Exception as e:  # noqa: BLE001 — connector boundary
            return ConnectorResponse(success=False, error=str(e))

    # ----------------------------------------------------------------- webhook
    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        if payload.get("type") == "url_verification":
            return []
        event = payload.get("event") or {}
        message = event.get("message") or {}
        if message.get("message_type") and message["message_type"] != "text":
            return []
        text = _extract_message_text(message)
        if not text:
            return []
        sender = (event.get("sender") or {}).get("sender_id") or {}
        return [
            ConnectorMessage(
                text=text,
                target={"chat_id": message.get("chat_id", "")},
                metadata={
                    "sender": sender.get("open_id"),
                    "message_id": message.get("message_id"),
                },
            )
        ]
