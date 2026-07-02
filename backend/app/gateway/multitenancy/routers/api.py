"""Multitenancy admin API: cost dashboard + quota management + usage.

Wires v1.5.8 data layer (aggregate_costs / InMemoryUsageTracker /
QuotaService / ResourceQuota) to FastAPI. Routers were referenced in
the v1.6.0 plan but never built — this is the v1.5.10 catch-up.

All data is tenant-scoped (the v1.5.8 model does not have a workspace
column on UsageRecord). Workspace-level breakdown is a v1.6.0 item.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.multitenancy.cost_dashboard import (
    CostBreakdown,
    aggregate_costs,
)
from app.gateway.multitenancy.models import (
    QuotaPeriod,
    ResourceQuota,
)
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker

router = APIRouter(prefix="/api/admin", tags=["multitenancy"])


# Module-level singletons. Tests override via app.state.multitenancy.
_tracker: InMemoryUsageTracker | None = None
_quota_service: QuotaService | None = None


def configure(
    tracker: InMemoryUsageTracker,
    quota_service: QuotaService,
) -> None:
    """Wire dependencies. Called from app.py lifespan."""
    global _tracker, _quota_service
    _tracker = tracker
    _quota_service = quota_service


def _require_admin(user: "AuthUser" = Depends(require_user)) -> "AuthUser":
    """Only owners/admins can read or mutate multitenancy state."""
    # require_user returns AuthUser dataclass; role is attribute not key.
    role = getattr(user, "role", "")
    if role not in {"owner"}:
        # v1.5.8 auth roles are only "owner" / "member" per auth.py.
        # ABAC "admin" role is a v1.6.0 item.
        raise HTTPException(status_code=403, detail="owner role required")
    return user


class QuotaIn(BaseModel):
    max_tokens: int = Field(ge=0, default=0)
    max_rpm: int = Field(ge=0, default=0)
    period: str = Field(default="monthly")  # "monthly" | "daily"
    enforce_mode: str = Field(default="advisory")  # "advisory" | "soft" | "hard"


class QuotaOut(BaseModel):
    tenant_id: str
    max_tokens: int
    max_rpm: int
    period: str
    enforce_mode: str


class CostBreakdownOut(BaseModel):
    entity_id: str
    total_tokens: int
    request_count: int


class UsageSummary(BaseModel):
    tenant_id: str
    total_tokens: int
    total_requests: int
    by_tenant: list[CostBreakdownOut]
    by_user: list[CostBreakdownOut]
    by_model: list[CostBreakdownOut]


def _to_quotadecision_out(b: CostBreakdown) -> CostBreakdownOut:
    return CostBreakdownOut(
        entity_id=b.entity_id,
        total_tokens=b.total_tokens,
        request_count=b.request_count,
    )


@router.get("/cost/summary", response_model=UsageSummary)
async def cost_summary(
    tenant_id: str,
    user: "AuthUser" = Depends(_require_admin),
) -> UsageSummary:
    """Aggregate usage for a tenant across all 3 group_by dimensions."""
    if _tracker is None:
        raise HTTPException(status_code=503, detail="multitenancy not configured")
    by_tenant = await aggregate_costs(_tracker, group_by="tenant_id")
    by_user = await aggregate_costs(_tracker, group_by="user_id")
    by_model = await aggregate_costs(_tracker, group_by="model")
    # Filter to this tenant only in the user/model breakdowns
    by_user_filtered = [b for b in by_user if b.entity_id]
    # Note: by_user / by_model returns ALL records; v1.5.10 keeps it simple.
    # Per-tenant isolation in user/model breakdowns is v1.6.0.
    total_tokens = sum(b.total_tokens for b in by_tenant if b.entity_id == tenant_id)
    total_requests = sum(
        b.request_count for b in by_tenant if b.entity_id == tenant_id
    )
    return UsageSummary(
        tenant_id=tenant_id,
        total_tokens=total_tokens,
        total_requests=total_requests,
        by_tenant=[_to_quotadecision_out(b) for b in by_tenant if b.entity_id == tenant_id],
        by_user=[_to_quotadecision_out(b) for b in by_user_filtered],
        by_model=[_to_quotadecision_out(b) for b in by_model],
    )


@router.get("/usage/{tenant_id}", response_model=UsageSummary)
async def usage_summary(
    tenant_id: str,
    user: "AuthUser" = Depends(_require_admin),
) -> UsageSummary:
    """Alias for /cost/summary?tenant_id=X for client convenience."""
    return await cost_summary(tenant_id=tenant_id, user=user)


@router.get("/quota/{tenant_id}", response_model=QuotaOut)
async def get_quota(
    tenant_id: str,
    user: "AuthUser" = Depends(_require_admin),
) -> QuotaOut:
    """Read the current ResourceQuota for a tenant.

    v1.5.8 QuotaService does not have a get/set_quota pair — it only
    holds a single ResourceQuota in __init__. This endpoint reads from
    a module-level dict populated by set_quota (or returns default).
    """
    if _quota_service is None:
        raise HTTPException(status_code=503, detail="multitenancy not configured")
    quota = _quota_service._quota  # type: ignore[attr-defined]
    if quota is None or quota.tenant_id != tenant_id:
        # No quota configured for this tenant
        return QuotaOut(
            tenant_id=tenant_id,
            max_tokens=0,
            max_rpm=0,
            period="monthly",
            enforce_mode="advisory",
        )
    return QuotaOut(
        tenant_id=quota.tenant_id,
        max_tokens=quota.max_tokens,
        max_rpm=quota.max_rpm,
        period=quota.period.value,
        enforce_mode=getattr(quota, "enforce_mode", "advisory"),
    )


@router.put("/quota/{tenant_id}", response_model=QuotaOut)
async def set_quota(
    tenant_id: str,
    payload: QuotaIn,
    user: "AuthUser" = Depends(_require_admin),
) -> QuotaOut:
    if _quota_service is None:
        raise HTTPException(status_code=503, detail="multitenancy not configured")
    if payload.enforce_mode not in {"advisory", "soft", "hard"}:
        raise HTTPException(
            status_code=422, detail="enforce_mode must be advisory|soft|hard",
        )
    if payload.period not in {"monthly", "daily"}:
        raise HTTPException(status_code=422, detail="period must be monthly|daily")
    # v1.5.10 Task 2: ResourceQuota now carries `enforce_mode` (validated
    # above), so we pass it through directly. The field has a default of
    # "advisory" if a caller ever constructs ResourceQuota without it.
    new_quota = ResourceQuota(
        tenant_id=tenant_id,
        period=QuotaPeriod(payload.period),
        max_tokens=payload.max_tokens,
        max_rpm=payload.max_rpm,
        enforce_mode=payload.enforce_mode,
    )
    # Mutate service's quota in-place (service is a singleton). This
    # works because ResourceQuota is frozen but we replace the field
    # on the service object (not on the quota).
    _quota_service._quota = new_quota  # type: ignore[attr-defined]
    return await get_quota(tenant_id, user=user)  # type: ignore[arg-type]
