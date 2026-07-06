"""Tests for canvas resource isolation (Task A9 of v1.6.x).

Lock down two behaviors:

1. ``enforce_mode="hard"`` on a quota blocks ``/execute`` with HTTP 429
   when ``estimated_tokens`` exceeds the configured ``max_tokens``.
2. Executing a workflow whose ``workspace_id`` differs from the
   caller's ``workspace_id`` returns 403 — the workspace isolation
   check that was introduced in A8 (workflows.py:278).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.canvas.routers.workflows import (
    configure,
    reset_for_tests,
)
from app.gateway.canvas.routers.workflows import (
    router as canvas_router,
)
from app.gateway.canvas.store import InMemoryWorkflowStore
from app.gateway.canvas.versions import InMemoryVersionStore, VersionManager
from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
from app.gateway.multitenancy.quota import QuotaService
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


def _owner():
    from app.gateway.auth import AuthUser

    return AuthUser(
        id="owner",
        email="o@x.com",
        role="owner",
        name="O",
        status="active",
        password_hash="x",
        salt="y",
    )


def _client_with_owner() -> TestClient:
    app = FastAPI()
    app.include_router(canvas_router)
    from app.gateway.auth import require_owner_user, require_user

    async def _override_user():
        return _owner()

    async def _override_owner():
        return _owner()

    app.dependency_overrides[require_user] = _override_user
    app.dependency_overrides[require_owner_user] = _override_owner
    return TestClient(app)


def test_quota_hard_mode_blocks_execute_with_429():
    """When enforce_mode='hard' and estimated_tokens > quota, /execute returns 429."""
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    tracker = InMemoryUsageTracker()
    quota = ResourceQuota(
        tenant_id="ws1",
        period=QuotaPeriod.MONTHLY,
        max_tokens=10,
        max_rpm=0,
        enforce_mode="hard",
    )
    qservice = QuotaService(usage=tracker, quota=quota)

    configure(
        wstore,
        VersionManager(wstore, vstore),
        quota_service=qservice,
    )

    client = _client_with_owner()
    created = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws1",
            "nodes": [
                {
                    "id": "n1",
                    "kind": "prompt",
                    "config": {"template": "x"},
                    "position": [0.0, 0.0],
                }
            ],
            "edges": [],
        },
    ).json()

    resp = client.post(
        f"/api/workflows/{created['id']}/execute",
        json={
            "inputs": {},
            "workspace_id": "ws1",
            "estimated_tokens": 100,
        },
    )
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "QUOTA_EXCEEDED"
    assert body["detail"]["error"]["mode"] == "hard"


def test_workflow_execute_rejects_other_workspace():
    """execute with workspace_id != workflow.workspace_id returns 403."""
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    # No quota_service: lock down the A8 403 check independently of A9 quota wiring.
    configure(wstore, VersionManager(wstore, vstore))

    client = _client_with_owner()
    created = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws1",
            "nodes": [
                {
                    "id": "n1",
                    "kind": "prompt",
                    "config": {"template": "x"},
                    "position": [0.0, 0.0],
                }
            ],
            "edges": [],
        },
    ).json()

    resp = client.post(
        f"/api/workflows/{created['id']}/execute",
        json={"inputs": {}, "workspace_id": "ws2"},  # mismatched
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["detail"]["error"]["code"] == "NOT_WORKSPACE_MEMBER"
