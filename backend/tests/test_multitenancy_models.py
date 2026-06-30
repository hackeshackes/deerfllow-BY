"""Tests for the multitenancy domain model."""
from __future__ import annotations

import pytest

from app.gateway.multitenancy.models import (
    Project,
    QuotaPeriod,
    ResourceQuota,
    Tenant,
    Workspace,
)


def test_workspace_belongs_to_tenant():
    t = Tenant(id="t-1", name="Acme")
    w = Workspace(id="w-1", name="Eng", tenant_id=t.id)
    assert w.tenant_id == t.id
    assert w.tenant_id == "t-1"


def test_project_nests_in_workspace():
    t = Tenant(id="t-1", name="Acme")
    w = Workspace(id="w-1", name="Eng", tenant_id=t.id)
    p = Project(id="p-1", name="API", workspace_id=w.id)
    assert p.workspace_id == w.id


def test_tenant_billing_email_optional():
    t = Tenant(id="t-2", name="Tiny")
    assert t.billing_email == ""


def test_quota_period_is_string_enum():
    assert QuotaPeriod.MONTHLY.value == "monthly"
    assert QuotaPeriod.DAILY.value == "daily"


def test_quota_rejects_negative_tokens():
    with pytest.raises(ValueError, match="max_tokens"):
        ResourceQuota(
            tenant_id="t-1",
            period=QuotaPeriod.MONTHLY,
            max_tokens=-1,
            max_rpm=60,
        )


def test_quota_rejects_negative_rpm():
    with pytest.raises(ValueError, match="max_rpm"):
        ResourceQuota(
            tenant_id="t-1",
            period=QuotaPeriod.MONTHLY,
            max_tokens=1000,
            max_rpm=-1,
        )


def test_quota_accepts_zero():
    """Zero is a valid quota (effectively disable the limit)."""
    q = ResourceQuota(
        tenant_id="t-1",
        period=QuotaPeriod.MONTHLY,
        max_tokens=0,
        max_rpm=0,
    )
    assert q.max_tokens == 0
    assert q.max_rpm == 0


def test_workspace_slug_optional():
    w = Workspace(id="w-1", name="Eng", tenant_id="t-1")
    assert w.slug == ""


def test_models_are_frozen():
    t = Tenant(id="t-1", name="Acme")
    with pytest.raises(Exception):  # FrozenInstanceError
        t.name = "Other"  # type: ignore[misc]
