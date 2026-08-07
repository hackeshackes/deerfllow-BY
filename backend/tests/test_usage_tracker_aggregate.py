"""Tests for the per-user / per-workspace usage aggregation (v1.7 M3.1)."""

from __future__ import annotations

import pytest

from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@pytest.mark.asyncio
async def test_aggregate_by_user():
    tracker = InMemoryUsageTracker()
    await tracker.record("ws-1", "u1", tokens=100, model="m", ts=1000.0)
    await tracker.record("ws-1", "u1", tokens=50, model="m", ts=1005.0)
    await tracker.record("ws-1", "u2", tokens=200, model="m", ts=1010.0)

    rows = await tracker.aggregate("user", since=0.0, until=2000.0)
    by_id = {r["id"]: r for r in rows}
    assert by_id["u1"]["tokens"] == 150
    assert by_id["u1"]["executions"] == 2
    assert by_id["u2"]["tokens"] == 200
    # Sorted by tokens desc.
    assert rows[0]["id"] == "u2"


@pytest.mark.asyncio
async def test_aggregate_by_workspace():
    tracker = InMemoryUsageTracker()
    await tracker.record("ws-1", "u1", tokens=100, model="m", ts=1000.0)
    await tracker.record("ws-2", "u2", tokens=300, model="m", ts=1010.0)

    rows = await tracker.aggregate("workspace", since=0.0, until=2000.0)
    by_id = {r["id"]: r for r in rows}
    assert by_id["ws-1"]["tokens"] == 100
    assert by_id["ws-2"]["tokens"] == 300


@pytest.mark.asyncio
async def test_aggregate_respects_time_window():
    tracker = InMemoryUsageTracker()
    await tracker.record("ws-1", "u1", tokens=100, model="m", ts=1000.0)
    await tracker.record("ws-1", "u1", tokens=500, model="m", ts=5000.0)

    rows = await tracker.aggregate("user", since=0.0, until=2000.0)
    assert rows[0]["tokens"] == 100  # only the in-window record


@pytest.mark.asyncio
async def test_aggregate_last_active_at():
    tracker = InMemoryUsageTracker()
    await tracker.record("ws-1", "u1", tokens=100, model="m", ts=1000.0)
    await tracker.record("ws-1", "u1", tokens=50, model="m", ts=1500.0)

    rows = await tracker.aggregate("user", since=0.0, until=2000.0)
    assert rows[0]["last_active_at"] == 1500.0


@pytest.mark.asyncio
async def test_aggregate_empty():
    tracker = InMemoryUsageTracker()
    assert await tracker.aggregate("user", since=0.0, until=2000.0) == []