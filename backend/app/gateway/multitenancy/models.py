"""Domain model for multi-tenant scoping.

Hierarchy:
- Tenant      (organization)
  - Workspace (team / department)
    - Project  (product / initiative)

Each thread, knowledge base, and connector instance is scoped to a
workspace. A user belongs to a tenant via membership; their active
workspace within that tenant is the runtime scope for all reads/writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QuotaPeriod(str, Enum):
    MONTHLY = "monthly"
    DAILY = "daily"


@dataclass(frozen=True)
class Tenant:
    id: str
    name: str
    """Optional billing contact email. May be empty in dev mode."""
    billing_email: str = ""


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    tenant_id: str
    """Display-only slug (no spaces, lowercase). Used in URLs."""
    slug: str = ""


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    workspace_id: str
    """Optional description surfaced in the cost dashboard."""
    description: str = ""


@dataclass(frozen=True)
class ResourceQuota:
    """Advisory quota applied to a tenant.

    v1.5.8 is advisory-only: when the limit is exceeded, callers receive
    a warning in the response but the operation is still allowed. The
    `enforce` flag is reserved for v1.5.9 when we have 1+ month of
    production telemetry to set sensible hard limits.
    """

    tenant_id: str
    period: QuotaPeriod
    max_tokens: int
    max_rpm: int  # requests per minute

    def __post_init__(self) -> None:
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be >= 0")
        if self.max_rpm < 0:
            raise ValueError("max_rpm must be >= 0")
