"""Base connector protocol and data types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorMessage:
    """Outgoing or incoming message."""
    text: str = ""
    target: dict = field(default_factory=dict)  # {chat_id, user_id, thread_id, ...}
    attachments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ConnectorResponse:
    """Result of send() or webhook processing."""
    success: bool
    external_id: str | None = None
    error: str | None = None
    raw: Any = None


class BaseConnector(ABC):
    """Abstract connector. Subclasses implement send + receive_webhook."""

    name: str = ""
    display_name: str = ""

    @abstractmethod
    async def send(self, message: ConnectorMessage) -> ConnectorResponse: ...

    @abstractmethod
    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]: ...

    async def health_check(self) -> bool:
        """Default: returns True. Override for connectivity checks."""
        return True