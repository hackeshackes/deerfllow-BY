"""Audit event domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import uuid


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AUTOMATION = "automation"
    CHANNEL = "channel"


@dataclass
class AuditEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actor_id: str = ""
    actor_type: ActorType = ActorType.USER
    action: str = ""  # e.g. "thread.create", "skill.enable", "config.update"
    resource_type: str = ""  # e.g. "thread", "skill", "config"
    resource_id: str | None = None
    workspace_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict = field(default_factory=dict)
    success: bool = True
    occurred_at: str = field(default_factory=lambda: "")  # ISO8601, set by writer

    def __post_init__(self):
        if not self.actor_id:
            raise ValueError("actor_id required")
        if not self.action:
            raise ValueError("action required")
        if not self.resource_type:
            raise ValueError("resource_type required")