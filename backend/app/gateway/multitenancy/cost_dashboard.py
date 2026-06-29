"""Cost dashboard — aggregate token usage by tenant / user / project.

The dashboard reads from a usage tracker and groups by a chosen
dimension. The admin UI calls this with a `group_by` parameter and
gets back a list of breakdowns the table can render directly.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .usage_tracker import InMemoryUsageTracker, UsageRecord


@dataclass(frozen=True)
class CostBreakdown:
    entity_id: str  # tenant_id, user_id, or project_id
    total_tokens: int
    request_count: int

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
        }


async def aggregate_costs(
    tracker: InMemoryUsageTracker,
    group_by: str = "tenant_id",
) -> list[CostBreakdown]:
    """Aggregate usage by the chosen field.

    Supported group_by values: 'tenant_id', 'user_id', 'model'.
    Any other value falls back to 'tenant_id' (most common dashboard view).
    """
    if group_by not in ("tenant_id", "user_id", "model"):
        group_by = "tenant_id"

    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    records: list[UsageRecord] = await tracker.all_records()
    for r in records:
        key = getattr(r, group_by)
        totals[key] += r.tokens
        counts[key] += 1

    return [
        CostBreakdown(entity_id=k, total_tokens=totals[k], request_count=counts[k])
        for k in sorted(totals.keys())
    ]
