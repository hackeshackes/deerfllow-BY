"""Subscription domain model.

A subscription is a user → target binding with a list of notification channels.
`target` is intentionally small: a (kind, id) pair. The subscriber list for a
target grows as users subscribe; the notification fan-out happens in
`SubscriptionService.handle_mention` (Task 17).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NotifyChannel(str, Enum):
    INAPP = "inapp"
    EMAIL = "email"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"


class TargetKind(str, Enum):
    THREAD = "thread"
    KNOWLEDGE = "knowledge"
    AUTOMATION = "automation"
    WORKFLOW = "workflow"
    USER = "user"
    DEPARTMENT = "department"
    PROJECT = "project"


@dataclass(frozen=True)
class SubscriptionTarget:
    kind: str  # TargetKind value
    id: str

    def __post_init__(self) -> None:
        valid = {t.value for t in TargetKind}
        if self.kind not in valid:
            raise ValueError(
                f"unknown target kind: {self.kind!r}; valid: {sorted(valid)}"
            )
        if not self.id:
            raise ValueError("target id must be non-empty")


@dataclass
class Subscription:
    id: str
    user_id: str
    target: SubscriptionTarget
    notify_via: list[NotifyChannel] = field(default_factory=list)
    created_at: str = ""
