"""Tests for the QuotaService (advisory mode in v1.5.8)."""
from __future__ import annotations

import pytest

from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@pytest.fixture
def service():
    return QuotaService(
        usage=InMemoryUsageTracker(),
        quota=ResourceQuota(
            tenant_id="t-1",
            period=QuotaPeriod.MONTHLY,
            max_tokens=1000,
            max_rpm=10,
        ),
    )


@pytest.mark.asyncio
async def test_first_request_under_limit(service):
    decision = await service.check_and_record(
        tenant_id="t-1", tokens=100, rpm_bucket="alice"
    )
    # `remaining` is computed AFTER the current request is recorded:
    # max(0, max_tokens - used - tokens) = 1000 - 100 - 100 = 800.
    assert decision.allowed is True
    assert decision.remaining_tokens == 800
    assert decision.remaining_rpm == 9
    assert decision.warnings == []


@pytest.mark.asyncio
async def test_exceeding_token_quota_warns_but_allows(service):
    decision = await service.check_and_record(
        tenant_id="t-1", tokens=2000, rpm_bucket="alice"
    )
    # v1.5.8: advisory — allowed stays True
    assert decision.allowed is True
    assert "token_quota_exceeded" in decision.warnings
    assert decision.remaining_tokens == 0  # capped at 0


@pytest.mark.asyncio
async def test_rpm_limit_warns_after_threshold(service):
    for i in range(10):
        await service.check_and_record(tenant_id="t-1", tokens=1, rpm_bucket=f"u{i}")
    decision = await service.check_and_record(
        tenant_id="t-1", tokens=1, rpm_bucket="u-new"
    )
    assert "rpm_limit_reached" in decision.warnings
    assert decision.remaining_rpm == 0


@pytest.mark.asyncio
async def test_zero_quota_means_disabled():
    """max_tokens=0 / max_rpm=0 → no limit; no warnings."""
    svc = QuotaService(
        usage=InMemoryUsageTracker(),
        quota=ResourceQuota(
            tenant_id="t-1", period=QuotaPeriod.MONTHLY, max_tokens=0, max_rpm=0
        ),
    )
    decision = await svc.check_and_record(tenant_id="t-1", tokens=999_999)
    assert decision.warnings == []
    assert decision.remaining_tokens == 0  # max=0, used=999_999, remaining=0


@pytest.mark.asyncio
async def test_quota_isolation_between_tenants(service):
    await service.check_and_record(tenant_id="t-1", tokens=900, rpm_bucket="a")
    decision = await service.check_and_record(tenant_id="t-2", tokens=100, rpm_bucket="b")
    # t-2 has its own bucket — 100 tokens consumed this request, so
    # remaining = 1000 - 100 - 100 = 800 (same shape as the single-tenant case)
    assert decision.remaining_tokens == 800


@pytest.mark.asyncio
async def test_decision_to_dict_round_trip(service):
    decision = await service.check_and_record(tenant_id="t-1", tokens=50)
    d = decision.to_dict()
    assert d["allowed"] is True
    assert "remaining_tokens" in d
    assert "warnings" in d
