"""Usage tracker — records token consumption and request rate per tenant.

In-memory implementation. Production swap: Postgres-backed (similar to
how `SqliteDLQStore` replaced `InMemoryDLQStore` in v1.5.7).
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class UsageRecord:
    tenant_id: str
    user_id: str
    model: str
    tokens: int
    timestamp: float


class InMemoryUsageTracker:
    """Tracks per-tenant token usage and per-(tenant, minute) request count."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        # Per-(tenant_id, minute_bucket) request count for RPM.
        self._rpm: dict[tuple[str, int], int] = defaultdict(int)
        self._lock = asyncio.Lock()

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
            self._records.append(
                UsageRecord(tenant_id, user_id, model, tokens, ts)
            )
            self._rpm[(tenant_id, self._minute_bucket(ts))] += 1

    async def tokens_in_window(
        self,
        tenant_id: str,
        window_start: float,
        window_end: float,
    ) -> int:
        async with self._lock:
            return sum(
                r.tokens
                for r in self._records
                if r.tenant_id == tenant_id
                and window_start <= r.timestamp < window_end
            )

    async def current_rpm(self, tenant_id: str) -> int:
        """Return the request count for the current minute bucket."""
        async with self._lock:
            return self._rpm.get((tenant_id, self._minute_bucket()), 0)

    async def all_records(self) -> list[UsageRecord]:
        async with self._lock:
            return list(self._records)
