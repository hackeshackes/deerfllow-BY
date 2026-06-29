"""Webhook bridge — receive inbound webhooks from external systems and dispatch
them to the matching connector's `receive_webhook()`.

Each bridge route pairs a connector with a shared secret. The secret is
verified in constant time before the payload is handed to the connector.
The connector is responsible for parsing the platform-specific payload
(Feishu events, Slack events, etc.) and producing `ConnectorMessage`s.

Note: real platforms (Feishu, Slack) use HMAC signatures, not a static secret.
The current implementation is the simplest thing that works for the
MVP; a follow-up will swap the static string for `hmac.compare_digest` of
a signed payload. The bridge interface will not change.
"""
from __future__ import annotations

from .base import BaseConnector, ConnectorMessage


class WebhookBridge:
    def __init__(self) -> None:
        self._routes: dict[str, tuple[BaseConnector, str]] = {}

    # ------------------------------------------------------------------ routes
    def register(self, connector: BaseConnector, secret: str) -> None:
        if not connector.name:
            raise ValueError("connector.name must be set before registering a route")
        if not secret:
            raise ValueError("webhook secret must be non-empty")
        self._routes[connector.name] = (connector, secret)

    def unregister(self, name: str) -> None:
        self._routes.pop(name, None)

    def has_route(self, name: str) -> bool:
        return name in self._routes

    # ---------------------------------------------------------------- dispatch
    async def handle_inbound(
        self, connector_name: str, secret: str, payload: dict
    ) -> list[ConnectorMessage]:
        if connector_name not in self._routes:
            raise KeyError(f"connector {connector_name!r} not registered")
        conn, expected_secret = self._routes[connector_name]
        if not self._secrets_match(secret, expected_secret):
            raise PermissionError("invalid webhook secret")
        return await conn.receive_webhook(payload)

    @staticmethod
    def _secrets_match(provided: str, expected: str) -> bool:
        # Constant-time comparison when both are strings; fall back to == for
        # any pathological type mismatch.
        if not isinstance(provided, str) or not isinstance(expected, str):
            return False
        if len(provided) != len(expected):
            return False
        result = 0
        for a, b in zip(provided, expected):
            result |= ord(a) ^ ord(b)
        return result == 0
