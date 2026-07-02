"""Tests for the multitenancy admin API router (v1.5.10 Task 1).

These tests wire the v1.5.8 data layer
(``InMemoryUsageTracker`` / ``QuotaService`` / ``aggregate_costs``)
to FastAPI through the new ``routers.api`` module.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.routers import api as mt_api
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@dataclass(slots=True)
class _StubUser:
    """Minimal AuthUser stand-in for dependency override (avoids file I/O)."""

    id: str = "u-1"
    email: str = "owner@test"
    role: str = "owner"
    name: str = "Stub Owner"
    status: str = "active"


def _override_user(owner: bool = True) -> AuthUser:
    return AuthUser(
        id="u-1",
        email="owner@test",
        role="owner" if owner else "member",
        name="Stub Owner",
        status="active",
        password_hash="x" * 32,
        salt="y" * 16,
    )


def _build_app(*, owner: bool = True) -> tuple[FastAPI, InMemoryUsageTracker, QuotaService]:
    """Build a fresh FastAPI client + configure the module-level singletons."""
    tracker = InMemoryUsageTracker()
    quota = ResourceQuota(
        tenant_id="default",
        period=QuotaPeriod.MONTHLY,
        max_tokens=0,
        max_rpm=0,
    )
    svc = QuotaService(usage=tracker, quota=quota)
    mt_api.configure(tracker=tracker, quota_service=svc)

    app = FastAPI()
    user = _override_user(owner=owner)

    async def _dep():
        return user

    app.dependency_overrides[require_user] = _dep
    app.include_router(mt_api.router)
    return app, tracker, svc


def test_cost_summary_filters_records_by_tenant():
    app, tracker, _ = _build_app()

    # Seed: 2 tenants, multiple users/models.
    import asyncio

    async def seed():
        await tracker.record(tenant_id="t-a", user_id="u-1", tokens=100, model="gpt-4")
        await tracker.record(tenant_id="t-a", user_id="u-2", tokens=200, model="gpt-4")
        await tracker.record(tenant_id="t-b", user_id="u-3", tokens=999, model="claude-3")

    asyncio.run(seed())

    client = TestClient(app)
    r = client.get("/api/admin/cost/summary", params={"tenant_id": "t-a"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == "t-a"
    assert body["total_tokens"] == 300
    assert body["total_requests"] == 2
    # by_tenant is filtered to tenant t-a (1 row).
    assert len(body["by_tenant"]) == 1
    assert body["by_tenant"][0]["entity_id"] == "t-a"
    assert body["by_tenant"][0]["total_tokens"] == 300
    # by_model aggregates everything (simplified path per plan Task 1).
    model_ids = {row["entity_id"] for row in body["by_model"]}
    assert {"gpt-4", "claude-3"}.issubset(model_ids)


def test_usage_by_tenant_id_aliases_cost_summary():
    app, tracker, _ = _build_app()
    import asyncio

    async def seed():
        await tracker.record(tenant_id="t-z", user_id="u", tokens=42, model="m")

    asyncio.run(seed())

    client = TestClient(app)
    r = client.get("/api/admin/usage/t-z")
    assert r.status_code == 200, r.text
    assert r.json()["tenant_id"] == "t-z"
    assert r.json()["total_tokens"] == 42


def test_get_quota_returns_default_for_unconfigured_tenant():
    app, _, _ = _build_app()
    client = TestClient(app)
    r = client.get("/api/admin/quota/some-new-tenant")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == "some-new-tenant"
    assert body["max_tokens"] == 0
    assert body["max_rpm"] == 0
    assert body["period"] == "monthly"
    # enforce_mode falls back to "advisory" (Task 2 field, defaults via getattr).
    assert body["enforce_mode"] == "advisory"


def test_put_quota_persists_and_get_reflects_update():
    app, _, _ = _build_app()
    client = TestClient(app)
    payload = {
        "max_tokens": 1000,
        "max_rpm": 30,
        "period": "daily",
        "enforce_mode": "advisory",
    }
    put_resp = client.put("/api/admin/quota/tenant-x", json=payload)
    assert put_resp.status_code == 200, put_resp.text
    put_body = put_resp.json()
    assert put_body["tenant_id"] == "tenant-x"
    assert put_body["max_tokens"] == 1000
    assert put_body["max_rpm"] == 30
    assert put_body["period"] == "daily"

    get_resp = client.get("/api/admin/quota/tenant-x")
    assert get_resp.status_code == 200, get_resp.text
    get_body = get_resp.json()
    assert get_body["max_tokens"] == 1000
    assert get_body["max_rpm"] == 30
    assert get_body["period"] == "daily"


def test_put_quota_rejects_invalid_enforce_mode():
    app, _, _ = _build_app()
    client = TestClient(app)
    payload = {
        "max_tokens": 100,
        "max_rpm": 0,
        "period": "monthly",
        "enforce_mode": "invalid-mode",
    }
    r = client.put("/api/admin/quota/tenant-x", json=payload)
    # Router-side validation (plan code) should reject before service call.
    assert r.status_code == 422
    assert "enforce_mode" in r.json()["detail"]


def test_put_quota_rejects_invalid_period():
    app, _, _ = _build_app()
    client = TestClient(app)
    payload = {
        "max_tokens": 100,
        "max_rpm": 0,
        "period": "yearly",
        "enforce_mode": "advisory",
    }
    r = client.put("/api/admin/quota/tenant-x", json=payload)
    assert r.status_code == 422
    assert "period" in r.json()["detail"]


def test_non_owner_role_is_forbidden():
    app, _, _ = _build_app(owner=False)  # role="member"
    client = TestClient(app)
    r = client.get("/api/admin/cost/summary", params={"tenant_id": "t-a"})
    assert r.status_code == 403
    # Same for the other admin endpoints.
    r2 = client.get("/api/admin/quota/anything")
    assert r2.status_code == 403
    r3 = client.get("/api/admin/usage/anything")
    assert r3.status_code == 403


def test_cost_summary_returns_503_when_not_configured():
    """Without ``configure()`` call, the router should return 503."""
    mt_api._tracker = None  # reset module-level singleton
    mt_api._quota_service = None

    app = FastAPI()
    user = _override_user(owner=True)

    async def _dep():
        return user

    app.dependency_overrides[require_user] = _dep
    app.include_router(mt_api.router)

    client = TestClient(app)
    r = client.get("/api/admin/cost/summary", params={"tenant_id": "t-a"})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()
