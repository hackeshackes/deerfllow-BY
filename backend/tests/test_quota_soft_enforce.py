"""Tests for ResourceQuota.enforce_mode + QuotaService.check_only."""
from __future__ import annotations

import pytest

from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@pytest.fixture
def tracker():
    return InMemoryUsageTracker()


@pytest.fixture
def make_service(tracker):
    def _make(enforce_mode: str = "advisory", max_tokens: int = 1000) -> QuotaService:
        q = ResourceQuota(
            tenant_id="t-1",
            period=QuotaPeriod.MONTHLY,
            max_tokens=max_tokens,
            max_rpm=0,
            enforce_mode=enforce_mode,
        )
        return QuotaService(usage=tracker, quota=q)
    return _make


@pytest.mark.asyncio
async def test_advisory_allows_overage_with_warning(make_service, tracker):
    svc = make_service(enforce_mode="advisory", max_tokens=1000)
    await tracker.record(tenant_id="t-1", user_id="u", tokens=900, model="x")
    decision = await svc.check_only(tenant_id="t-1", tokens=500)
    assert decision.allowed is True
    assert "token_quota_exceeded" in decision.warnings


@pytest.mark.asyncio
async def test_soft_allows_overage_with_warning(make_service, tracker):
    svc = make_service(enforce_mode="soft", max_tokens=1000)
    await tracker.record(tenant_id="t-1", user_id="u", tokens=950, model="x")
    decision = await svc.check_only(tenant_id="t-1", tokens=200)
    assert decision.allowed is True
    assert "token_quota_exceeded" in decision.warnings


@pytest.mark.asyncio
async def test_hard_blocks_overage(make_service, tracker):
    svc = make_service(enforce_mode="hard", max_tokens=1000)
    await tracker.record(tenant_id="t-1", user_id="u", tokens=950, model="x")
    decision = await svc.check_only(tenant_id="t-1", tokens=200)
    assert decision.allowed is False
    assert "token_quota_exceeded" in decision.warnings


@pytest.mark.asyncio
async def test_disabled_when_limit_is_zero(make_service):
    svc = make_service(enforce_mode="advisory", max_tokens=0)
    decision = await svc.check_only(tenant_id="t-1", tokens=999_999_999)
    assert decision.allowed is True
    # 0 = unlimited, no warning should fire
    assert "token_quota_exceeded" not in decision.warnings


@pytest.mark.asyncio
async def test_check_only_does_not_record(make_service, tracker):
    svc = make_service(enforce_mode="advisory", max_tokens=1000)
    decision = await svc.check_only(tenant_id="t-1", tokens=500)
    assert decision.allowed is True
    # check_only should not have mutated the tracker
    records = await tracker.all_records()
    assert len(records) == 0