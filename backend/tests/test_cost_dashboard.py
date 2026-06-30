"""Tests for the cost dashboard aggregation."""
from __future__ import annotations

import pytest

from app.gateway.multitenancy.cost_dashboard import aggregate_costs
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@pytest.mark.asyncio
async def test_aggregate_groups_by_tenant_id():
    tracker = InMemoryUsageTracker()
    await tracker.record("t-1", "alice", tokens=100, model="haiku")
    await tracker.record("t-1", "bob", tokens=200, model="haiku")
    await tracker.record("t-2", "carol", tokens=500, model="sonnet")
    breakdown = await aggregate_costs(tracker, group_by="tenant_id")
    by_tenant = {b.entity_id: b.total_tokens for b in breakdown}
    assert by_tenant["t-1"] == 300
    assert by_tenant["t-2"] == 500
    # request_count is per-record, so 2 for t-1, 1 for t-2
    counts = {b.entity_id: b.request_count for b in breakdown}
    assert counts["t-1"] == 2
    assert counts["t-2"] == 1


@pytest.mark.asyncio
async def test_aggregate_groups_by_user_id():
    tracker = InMemoryUsageTracker()
    await tracker.record("t-1", "alice", tokens=100, model="haiku")
    await tracker.record("t-1", "alice", tokens=50, model="haiku")
    await tracker.record("t-1", "bob", tokens=200, model="haiku")
    breakdown = await aggregate_costs(tracker, group_by="user_id")
    by_user = {b.entity_id: (b.total_tokens, b.request_count) for b in breakdown}
    assert by_user["alice"] == (150, 2)
    assert by_user["bob"] == (200, 1)


@pytest.mark.asyncio
async def test_aggregate_groups_by_model():
    tracker = InMemoryUsageTracker()
    await tracker.record("t-1", "alice", tokens=100, model="haiku")
    await tracker.record("t-1", "bob", tokens=200, model="sonnet")
    breakdown = await aggregate_costs(tracker, group_by="model")
    by_model = {b.entity_id: b.total_tokens for b in breakdown}
    assert by_model["haiku"] == 100
    assert by_model["sonnet"] == 200


@pytest.mark.asyncio
async def test_unknown_group_by_falls_back_to_tenant():
    tracker = InMemoryUsageTracker()
    await tracker.record("t-1", "alice", tokens=100, model="haiku")
    breakdown = await aggregate_costs(tracker, group_by="nonsense")
    assert len(breakdown) == 1
    assert breakdown[0].entity_id == "t-1"


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_list():
    tracker = InMemoryUsageTracker()
    breakdown = await aggregate_costs(tracker)
    assert breakdown == []


@pytest.mark.asyncio
async def test_to_dict_round_trip():
    tracker = InMemoryUsageTracker()
    await tracker.record("t-1", "alice", tokens=100, model="haiku")
    breakdown = await aggregate_costs(tracker)
    d = breakdown[0].to_dict()
    assert d == {
        "entity_id": "t-1",
        "total_tokens": 100,
        "request_count": 1,
    }
