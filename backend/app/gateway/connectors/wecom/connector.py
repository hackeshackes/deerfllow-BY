"""WeCom (企业微信) connector.

Implements `BaseConnector` against the WeCom OpenAPI:
- Outbound: send application text message to a user
- Inbound: receive text callback event

The access token is cached for the process lifetime. The expires_in field is
returned by the API but not currently used to refresh proactively — the next
401 from the API will trigger a re-fetch (TODO).
"""
from __future__ import annotations

import httpx

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse

WECOM_BASE = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComConnector(BaseConnector):
    name = "wecom"
    display_name = "WeCom (企业微信)"

    def __init__(self, bot_id: str, bot_secret: str, timeout: float = 10.0) -> None:
        if not bot_id or not bot_secret:
            raise ValueError("bot_id and bot_secret are required")
        self._bot_id = bot_id
        self._bot_secret = bot_secret
        self._timeout = timeout
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{WECOM_BASE}/gettoken",
                params={"corpid": self._bot_id, "corpsecret": self._bot_secret},
            )
            data = resp.json()
            if data.get("errcode") not in (0, None):
                raise RuntimeError(
                    f"wecom token error: errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
                )
            token = data.get("access_token")
            if not token:
                raise RuntimeError(f"wecom token missing in response: {data}")
            self._token = token
            return self._token

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        try:
            user_id = message.target.get("user_id", "")
            if not user_id:
                return ConnectorResponse(
                    success=False, error="wecom send requires user_id"
                )
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{WECOM_BASE}/message/send",
                    params={"access_token": token},
                    json={
                        "touser": user_id,
                        "msgtype": "text",
                        "agentid": 0,
                        "text": {"content": message.text},
                    },
                )
            data = resp.json()
            if data.get("errcode") == 0:
                return ConnectorResponse(success=True, raw=data)
            return ConnectorResponse(
                success=False,
                error=f"wecom api error: errcode={data.get('errcode')} errmsg={data.get('errmsg')}",
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResponse(success=False, error=str(e))

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        text = payload.get("Content")
        if not isinstance(text, str) or not text:
            return []
        from_user = payload.get("FromUserName", "")
        return [
            ConnectorMessage(
                text=text,
                target={"user_id": from_user},
                metadata={"sender": from_user},
            )
        ]
