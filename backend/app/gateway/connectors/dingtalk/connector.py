"""DingTalk connector.

Implements `BaseConnector` against the DingTalk Open Platform:
- Outbound: send group message via the robot webhook
- Inbound: receive event-callback webhook

The access token is cached for the process lifetime; the response does not
include an `expireIn` we can rely on, so the next 401 from the API will
trigger a re-fetch (TODO — not yet implemented in this MVP).
"""
from __future__ import annotations

import json

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse
from ..token_refresh import CachedToken

DINGTALK_BASE = "https://api.dingtalk.com"


class DingTalkConnector(BaseConnector):
    name = "dingtalk"
    display_name = "DingTalk"

    def __init__(self, client_id: str, client_secret: str, timeout: float = 10.0) -> None:
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._token_cache: CachedToken | None = None

    async def _get_token(self) -> str:
        if self._token_cache is None:
            self._token_cache = CachedToken(
                fetcher=self._fetch_token,
                ttl_seconds=5400,
            )
        return await self._token_cache.get()

    async def _fetch_token(self) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{DINGTALK_BASE}/v1.0/oauth2/accessToken",
                json={"appKey": self._client_id, "appSecret": self._client_secret},
            )
            data = resp.json()
            token = data.get("accessToken")
            if not token:
                raise RuntimeError(f"dingtalk token error: {data}")
            return token

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        try:
            token = await self._get_token()
            chat_id = message.target.get("chat_id", "")
            if not chat_id:
                return ConnectorResponse(
                    success=False, error="dingtalk send requires chat_id"
                )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{DINGTALK_BASE}/v1.0/robot/groupMessages/send",
                    headers={
                        "x-acs-dingtalk-access-token": token,
                        "Content-Type": "application/json",
                    },
                    json={
                        "msgParam": json.dumps({"text": {"content": message.text}}),
                        "msgKey": "sampleText",
                        "robotCode": self._client_id,
                        "openConversationId": chat_id,
                    },
                )
            data = resp.json()
            if "processQueryKey" in data:
                return ConnectorResponse(
                    success=True, external_id=data["processQueryKey"], raw=data
                )
            err = data.get("errmsg") or json.dumps(data)
            return ConnectorResponse(success=False, error=f"dingtalk api error: {err}")
        except Exception as e:  # noqa: BLE001
            return ConnectorResponse(success=False, error=str(e))

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        text_obj = payload.get("text")
        if not isinstance(text_obj, dict):
            return []
        text = text_obj.get("content")
        if not isinstance(text, str) or not text:
            return []
        return [
            ConnectorMessage(
                text=text,
                target={"chat_id": payload.get("conversationId", "")},
                metadata={"sender": payload.get("senderId")},
            )
        ]
