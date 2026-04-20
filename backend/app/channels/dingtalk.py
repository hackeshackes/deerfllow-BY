"""DingTalk channel — connects to DingTalk via webhook or SDK."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.channels.base import Channel
from app.channels.message_bus import MessageBus, OutboundMessage, ResolvedAttachment

logger = logging.getLogger(__name__)


class DingTalkChannel(Channel):
    """DingTalk IM channel using webhook mode.

    Configuration keys (in ``config.yaml`` under ``channels.dingtalk``):
        - ``client_id``: DingTalk application Client ID.
        - ``client_secret``: DingTalk application Client Secret.
        - ``webhook_url``: (optional) Custom webhook URL for notifications.

    This implementation supports webhook-based outbound notifications.
    Inbound message support requires additional setup with DingTalk streaming mode.
    """

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__(name="dingtalk", bus=bus, config=config)
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._webhook_url: str | None = None
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def start(self) -> None:
        if self._running:
            return

        self._client_id = self.config.get("client_id")
        self._client_secret = self.config.get("client_secret")
        self._webhook_url = self.config.get("webhook_url")

        if not self._client_id or not self._client_secret:
            logger.error("DingTalk channel requires client_id and client_secret")
            return

        logger.info("DingTalk channel initialized (webhook mode)")
        self._running = True
        self.bus.subscribe_outbound(self._on_outbound)

    async def stop(self) -> None:
        self._running = False
        self.bus.unsubscribe_outbound(self._on_outbound)
        logger.info("DingTalk channel stopped")

    async def send(self, msg: OutboundMessage, *, _max_retries: int = 3) -> None:
        if not self._webhook_url:
            logger.warning("[DingTalk] webhook_url not configured, skipping send")
            return

        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for DingTalk webhook mode")
            return

        markdown_content = msg.text
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "DeerFlow Agent Response",
                "text": markdown_content,
            },
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(_max_retries):
                try:
                    response = await client.post(
                        self._webhook_url,
                        json=payload,
                        timeout=30.0,
                    )
                    if response.status_code == 200:
                        logger.info("[DingTalk] message sent successfully")
                        return
                    logger.warning(
                        "[DingTalk] send failed (attempt %d/%d): %s",
                        attempt + 1,
                        _max_retries,
                        response.status_code,
                    )
                except Exception as exc:
                    logger.warning(
                        "[DingTalk] send failed (attempt %d/%d): %s",
                        attempt + 1,
                        _max_retries,
                        exc,
                    )
                    if attempt < _max_retries - 1:
                        await asyncio.sleep(2**attempt)

        logger.error("[DingTalk] failed to send message after %d attempts", _max_retries)

    async def send_file(self, msg: OutboundMessage, attachment: ResolvedAttachment) -> bool:
        if not self._webhook_url:
            return False
        logger.debug("[DingTalk] file upload not implemented in webhook mode")
        return False

    async def _on_outbound(self, msg: OutboundMessage) -> None:
        if msg.channel_name != self.name:
            return
        try:
            await self.send(msg)
        except Exception:
            logger.exception("Failed to send outbound message on channel %s", self.name)
