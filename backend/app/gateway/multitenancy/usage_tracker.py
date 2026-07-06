"""Usage tracker — records token consumption and request rate per tenant.

In-memory implementation. Production swap: Postgres-backed (similar to
how `SqliteDLQStore` replaced `InMemoryDLQStore` in v1.5.7).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from .models import ResourceQuota


@dataclass
class UsageRecord:
    tenant_id: str
    user_id: str
    model: str
    tokens: int
    timestamp: float


@dataclass(frozen=True)
class QuotaPreCheckDecision:
    """Outcome of a synchronous pre-execution quota check (Task A9).

    Returned by ``InMemoryUsageTracker.quota_pre_check``. Distinct from
    ``QuotaDecision`` because:

    - This decision is consulted BEFORE any usage is recorded, so the
      caller (canvas router) can refuse execution early.
    - The shape is intentionally tiny so the gateway does not depend
      on the full ``QuotaDecision`` (which has ``remaining_tokens``,
      ``remaining_rpm``, ``warnings``).
    - ``mode`` reports which ``ResourceQuota.enforce_mode`` was applied
      so the caller can surface it in the 429 response payload.

    ``remaining`` is the configured ``max_tokens`` (post-cap), or
    ``-1`` when no quota is configured — callers should treat
    ``remaining == -1`` as "no quota" rather than "zero remaining".
    """

    allowed: bool
    remaining: int
    mode: str


class InMemoryUsageTracker:
    """Tracks per-tenant token usage and per-(tenant, minute) request count."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        # Per-(tenant_id, minute_bucket) request count for RPM.
        self._rpm: dict[tuple[str, int], int] = defaultdict(int)
        self._lock = asyncio.Lock()
        # Optional fallback quota set by ``QuotaService.__init__`` so
        # ``quota_pre_check`` can answer without taking the tracker as
        # a dependency at call time. ``None`` means "no quota configured
        # for this workspace" — callers should not block.
        self._fallback_quota: ResourceQuota | None = None

    @staticmethod
    def _minute_bucket(ts: float | None = None) -> int:
        return int((ts if ts is not None else time.time()) // 60)

    def set_quota(self, quota: ResourceQuota | None) -> None:
        """Set (or clear) the fallback quota used by `quota_pre_check`.

        Why a setter rather than a constructor parameter: the tracker is
        constructed by the FastAPI lifespan before the quota is configured;
        the canvas router wires the quota in via `configure()` after both
        the tracker and the QuotaService exist.
        """
        self._fallback_quota = quota

    def quota_pre_check(
        self,
        workspace_id: str,
        estimated_tokens: int,
    ) -> QuotaPreCheckDecision:
        """Synchronous, recording-free quota check for the canvas router.

        Returns a ``QuotaPreCheckDecision`` describing whether
        ``estimated_tokens`` would be permitted by the configured
        ``ResourceQuota`` (if any):

        - No quota configured → ``allowed=True, remaining=-1,
          mode="advisory"``. The router must NOT block.
        - Quota with ``enforce_mode != "hard"`` → always allowed;
          ``remaining`` reflects ``max_tokens`` (clamped at 0).
        - Quota with ``enforce_mode == "hard"`` AND
          ``estimated_tokens > max_tokens`` → ``allowed=False``.

        ``max_tokens == 0`` means "unlimited" — the quota does not
        block regardless of ``enforce_mode``.
        """
        quota = self._fallback_quota
        if quota is None:
            return QuotaPreCheckDecision(allowed=True, remaining=-1, mode="advisory")

        # Unlimited quota (max_tokens == 0) never blocks, even in hard mode.
        if quota.max_tokens <= 0:
            return QuotaPreCheckDecision(
                allowed=True,
                remaining=-1,
                mode=quota.enforce_mode,
            )

        if quota.enforce_mode == "hard" and estimated_tokens > quota.max_tokens:
            return QuotaPreCheckDecision(
                allowed=False,
                remaining=max(0, quota.max_tokens),
                mode="hard",
            )

        return QuotaPreCheckDecision(
            allowed=True,
            remaining=max(0, quota.max_tokens),
            mode=quota.enforce_mode,
        )

    @staticmethod
    def _minute_bucket(ts: float | None = None) -> int:
        return int((ts if ts is not None else time.time()) // 60)

    async def record(
        self,
        tenant_id: str,
        user_id: str,
        tokens: int,
        model: str,
        ts: float | None = None,
    ) -> None:
        ts = ts if ts is not None else time.time()
        async with self._lock:
            self._records.append(UsageRecord(tenant_id, user_id, model, tokens, ts))
            self._rpm[(tenant_id, self._minute_bucket(ts))] += 1

    async def tokens_in_window(
        self,
        tenant_id: str,
        window_start: float,
        window_end: float,
    ) -> int:
        async with self._lock:
            return sum(r.tokens for r in self._records if r.tenant_id == tenant_id and window_start <= r.timestamp < window_end)

    async def current_rpm(self, tenant_id: str) -> int:
        """Return the request count for the current minute bucket."""
        async with self._lock:
            return self._rpm.get((tenant_id, self._minute_bucket()), 0)

    async def all_records(self) -> list[UsageRecord]:
        async with self._lock:
            return list(self._records)
