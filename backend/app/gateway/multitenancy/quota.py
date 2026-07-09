"""Quota service — advisory-only in v1.5.8.

The service records usage and emits warnings when the configured
`ResourceQuota` is exceeded, but does NOT block the request. The
caller surfaces the warnings (e.g. as a banner in the chat UI) so
operators can adjust quotas before they need to be enforced.

Switching to enforcement is a one-line change in `QuotaDecision` —
add an `enforce: bool` flag and a `deny_reason` field, and have
the gateway check `decision.allowed` before routing the request.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .models import ResourceQuota
from .usage_tracker import InMemoryUsageTracker

# In-memory usage tracker is the default; production swaps in a
# Postgres-backed tracker at app construction time.
_DefaultTracker = InMemoryUsageTracker


@dataclass
class QuotaDecision:
    allowed: bool
    remaining_tokens: int
    remaining_rpm: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "remaining_tokens": self.remaining_tokens,
            "remaining_rpm": self.remaining_rpm,
            "warnings": self.warnings,
        }


class QuotaService:
    def __init__(
        self,
        usage: InMemoryUsageTracker,
        quota: ResourceQuota,
    ) -> None:
        self._usage = usage
        self._quota = quota

    async def check_and_record(
        self,
        tenant_id: str,
        tokens: int,
        rpm_bucket: str | None = None,
        ts: float | None = None,
        workflow_id: str | None = None,
    ) -> QuotaDecision:
        """Record a request's token usage and return the quota decision.

        In v1.5.8 this is advisory only. The caller is expected to
        surface `decision.warnings` to the user.

        v1.6.1: optionally stamp ``workflow_id`` so quota audits can
        attribute consumption to a specific producing resource. Default
        ``None`` preserves backward compatibility with chat-run callers.
        """
        now = ts if ts is not None else time.time()
        await self._usage.record(
            tenant_id=tenant_id,
            user_id=rpm_bucket or "anon",
            tokens=tokens,
            model="unknown",
            ts=now,
            workflow_id=workflow_id,
        )

        warnings: list[str] = []
        # Token usage: aggregate over the last 30 days for monthly quota.
        if self._quota.period.value == "monthly":
            window_start = now - 30 * 86400
        else:
            window_start = now - 86400
        used = await self._usage.tokens_in_window(
            tenant_id, window_start=window_start, window_end=now + 1
        )
        remaining_tokens = max(0, self._quota.max_tokens - used - tokens)
        if used + tokens > self._quota.max_tokens and self._quota.max_tokens > 0:
            warnings.append("token_quota_exceeded")

        # RPM check: current minute bucket.
        rpm_used = await self._usage.current_rpm(tenant_id)
        remaining_rpm = max(0, self._quota.max_rpm - rpm_used)
        if rpm_used >= self._quota.max_rpm and self._quota.max_rpm > 0:
            warnings.append("rpm_limit_reached")

        return QuotaDecision(
            allowed=True,
            remaining_tokens=remaining_tokens,
            remaining_rpm=remaining_rpm,
            warnings=warnings,
        )

    async def check_only(
        self,
        tenant_id: str,
        tokens: int,
    ) -> QuotaDecision:
        """Check quota WITHOUT recording usage.

        Useful for admin UIs (preview the impact of a request) and for
        the v1.5.10 cost dashboard. Does NOT mutate the usage tracker.
        Honors `enforce_mode`:
        - "advisory": always allowed, warning only
        - "soft":     always allowed, warning only (same as advisory)
        - "hard":     denied when overage, warning + allowed=False

        Returns a QuotaDecision with `allowed` reflecting the enforce_mode.
        """
        now = time.time()
        warnings: list[str] = []
        if self._quota.period.value == "monthly":
            window_start = now - 30 * 86400
        else:
            window_start = now - 86400
        used = await self._usage.tokens_in_window(
            tenant_id, window_start=window_start, window_end=now + 1
        )
        rpm_used = await self._usage.current_rpm(tenant_id)

        token_overage = (used + tokens) > self._quota.max_tokens > 0
        rpm_overage = rpm_used >= self._quota.max_rpm > 0

        if token_overage:
            warnings.append("token_quota_exceeded")
        if rpm_overage:
            warnings.append("rpm_limit_reached")

        # Default: advisory / soft → always allow
        allowed = True
        if self._quota.enforce_mode == "hard" and (token_overage or rpm_overage):
            allowed = False

        remaining_tokens = max(0, self._quota.max_tokens - used - tokens)
        remaining_rpm = max(0, self._quota.max_rpm - rpm_used)

        return QuotaDecision(
            allowed=allowed,
            remaining_tokens=remaining_tokens,
            remaining_rpm=remaining_rpm,
            warnings=warnings,
        )

    async def record_usage(
        self,
        tokens: int,
        model: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
    ) -> None:
        """Record token usage WITHOUT consulting the quota decision.

        v1.6.1: used by the canvas ``/execute`` route *after* a
        workflow has actually run — the per-route decision is made by
        ``tracker.quota_pre_check`` (synchronous) and the post-execute
        accounting happens here. Recording without a quota decision
        avoids the cost of recomputing the same windows twice.

        ``tenant_id`` and ``user_id`` are required because this entry
        point may be invoked from outside any HTTP-request lifecycle
        (e.g. the canvas router, where the workspace id is the tenant
        scope and the session user is the consumer).
        """
        if tenant_id is None or user_id is None:
            raise ValueError("tenant_id and user_id are required for record_usage")
        await self._usage.record(
            tenant_id=tenant_id,
            user_id=user_id,
            tokens=tokens,
            model=model,
            workflow_id=workflow_id,
        )
