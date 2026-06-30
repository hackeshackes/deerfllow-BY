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
    ) -> QuotaDecision:
        """Record a request's token usage and return the quota decision.

        In v1.5.8 this is advisory only. The caller is expected to
        surface `decision.warnings` to the user.
        """
        now = ts if ts is not None else time.time()
        await self._usage.record(
            tenant_id=tenant_id,
            user_id=rpm_bucket or "anon",
            tokens=tokens,
            model="unknown",
            ts=now,
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
