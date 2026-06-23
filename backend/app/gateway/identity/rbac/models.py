"""RBAC v2 domain models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceType(str, Enum):
    WORKSPACE = "workspace"
    THREAD = "thread"
    KNOWLEDGE = "knowledge"
    AGENT = "agent"
    SKILL = "skill"
    AUTOMATION = "automation"
    CONNECTOR = "connector"
    CONFIG = "config"


class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class RoleScope(str, Enum):
    SYSTEM = "system"
    DEPARTMENT = "department"
    PROJECT = "project"


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    scope: str  # RoleScope value
    description: str | None = None


@dataclass(frozen=True)
class RoleBinding:
    id: str
    user_id: str
    role_id: str
    scope: str  # RoleScope value
    scope_id: str | None  # department_id or project_id; None for system

    def __post_init__(self):
        if self.scope != RoleScope.SYSTEM.value and not self.scope_id:
            raise ValueError("scope_id required for non-system role binding")
