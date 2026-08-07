"""Integration tests for the per-user / per-workspace quota usage endpoint (v1.7 M3.1).

GET /api/admin/quota/usage?group_by=user|workspace&since&until&limit&cursor
returns paginated per-dimension breakdowns from the usage tracker.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.routers import api as mt_api
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


def _build_app() -> tuple[FastAPI, InMemoryUsageTracker]:
    tracker = InMemoryUsageTracker()
    quota = ResourceQuota(tenant_id="default", period=QuotaPeriod.MONTHLY, max_tokens=0, max_rpm=0)
    svc = QuotaService(usage=tracker, quota=quota)
    mt_api.configure(tracker=tracker, quota_service=svc)

    app = FastAPI()

    def _owner():
        return AuthUser(
            id="u-owner",
            email="owner@test",
            role="owner",
            name="Owner",
            status="active",
            password_hash="x" * 32,
            salt="y" * 16,
        )

    app.dependency_overrides[require_user] = _owner
    app.include_router(mt_api.router)
    return app, tracker


@pytest.fixture
def client():
    app, tracker = _build_app()
    # Seed deterministic usage with realistic (recent) timestamps so records
    # land inside the endpoint's default 30-day window.
    import asyncio
    import time

    now = time.time()
    t1, t2, t3 = now - 5, now - 4, now - 3

    async def seed():
        await tracker.record("ws-1", "u1", tokens=100, model="m", ts=t1)
        await tracker.record("ws-1", "u1", tokens=50, model="m", ts=t2)
        await tracker.record("ws-2", "u2", tokens=300, model="m", ts=t3)

    asyncio.run(seed())
    with TestClient(app) as tc:
        yield tc


def test_group_by_user(client: TestClient):
    resp = client.get("/api/admin/quota/usage", params={"group_by": "user"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["group_by"] == "user"
    by_id = {r["id"]: r for r in body["rows"]}
    assert by_id["u1"]["tokens"] == 150
    assert by_id["u1"]["executions"] == 2
    assert by_id["u2"]["tokens"] == 300
    # Sorted by tokens desc.
    assert body["rows"][0]["id"] == "u2"
    assert body["total"] == 2


def test_group_by_workspace(client: TestClient):
    resp = client.get("/api/admin/quota/usage", params={"group_by": "workspace"})
    assert resp.status_code == 200, resp.text
    by_id = {r["id"]: r for r in resp.json()["rows"]}
    assert by_id["ws-1"]["tokens"] == 150
    assert by_id["ws-2"]["tokens"] == 300


def test_date_range_filter(client: TestClient):
    import time

    now = time.time()
    # Window includes u1's two records (now-5, now-4) but excludes u2 (now-3).
    resp = client.get(
        "/api/admin/quota/usage",
        params={"group_by": "user", "since": str(now - 4.5), "until": str(now - 3.5)},
    )
    assert resp.status_code == 200, resp.text
    tokens = {r["id"]: r["tokens"] for r in resp.json()["rows"]}
    assert tokens == {"u1": 50}  # only the now-4 record is inside the window


def test_pagination(client: TestClient):
    # limit=1 should paginate to u2 first (highest tokens), then u1.
    resp = client.get("/api/admin/quota/usage", params={"group_by": "user", "limit": 1})
    body = resp.json()
    assert len(body["rows"]) == 1
    assert body["rows"][0]["id"] == "u2"
    assert body["total"] == 2
    assert body["next_cursor"] == 1


def test_member_denied():
    app, tracker = _build_app()
    app.dependency_overrides[require_user] = lambda: AuthUser(
        id="m",
        email="m@test",
        role="member",
        name="M",
        status="active",
        password_hash="x" * 32,
        salt="y" * 16,
    )
    with TestClient(app) as client:
        resp = client.get("/api/admin/quota/usage", params={"group_by": "user"})
        assert resp.status_code == 403