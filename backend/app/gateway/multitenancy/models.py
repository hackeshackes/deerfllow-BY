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
    """Advisory / soft / hard quota applied to a tenant.

    v1.5.8 was advisory-only. v1.5.10 adds `enforce_mode`:

    - "advisory" (default): overage produces warnings but does not block.
    - "soft":              same as advisory today; reserved for a future
                           differentiation (e.g. budget-driven auto-throttle).
    - "hard":              overage produces `QuotaDecision.allowed=False`.

    `max_tokens=0` / `max_rpm=0` means "unlimited" — overage warnings never
    fire, regardless of `enforce_mode`.
    """

    tenant_id: str
    period: QuotaPeriod
    max_tokens: int
    max_rpm: int  # requests per minute
    enforce_mode: str = "advisory"  # "advisory" | "soft" | "hard"

    def __post_init__(self) -> None:
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be >= 0")
        if self.max_rpm < 0:
            raise ValueError("max_rpm must be >= 0")
        if self.enforce_mode not in {"advisory", "soft", "hard"}:
            raise ValueError("enforce_mode must be advisory|soft|hard")
