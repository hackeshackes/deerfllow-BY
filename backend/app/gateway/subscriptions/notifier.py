"""Notifier implementations.

`InMemoryNotifier` is the test / development implementation. The production
implementation will fan out to email + the registered IM connectors
(feishu / dingtalk / wecom). The contract is intentionally minimal:
`send(notification) -> bool` is the only method callers depend on.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Notification:
    recipient: str
    text: str
    metadata: dict = field(default_factory=dict)


class InMemoryNotifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> bool:
        self.sent.append(notification)
        return True
