"""Tests for the v1.6.1 workflow_id linkage on quota usage records.

Closes a v1.6.0-canvas known-limitation (release notes § v1.6.1
backlog): usage history was scoped only by tenant, with no reverse
pointer from a usage row to the specific Workflow that produced it.

These tests lock down:

1. ``record()`` accepts an optional ``workflow_id`` and stamps it
   onto the ``UsageRecord``.
2. ``tokens_in_window_for_workflow`` returns the per-workflow total
   so a quota audit can attribute consumption to a specific
   workflow.
3. The canvas ``/execute`` route forwards ``workflow_id`` into the
   tracker's ``record`` call so the usage history is wired end-to-end.
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
from app.gateway.multitenancy.usage_tracker import InMemoryUsageTracker, UsageRecord


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


def _quota_service() -> QuotaService:
    tracker = InMemoryUsageTracker()
    quota = ResourceQuota(
        tenant_id="ws1",
        period=QuotaPeriod.MONTHLY,
        # Unlimited so we can hit the execute path without 429. The
        # test asserts the usage-history wiring, not the quota gate.
        max_tokens=0,
        max_rpm=0,
        enforce_mode="advisory",
    )
    return QuotaService(usage=tracker, quota=quota)


# ---- Pure unit tests on the tracker ----


@pytest.mark.asyncio
async def test_record_attaches_workflow_id_when_provided():
    tracker = InMemoryUsageTracker()
    await tracker.record(
        tenant_id="ws1",
        user_id="u1",
        tokens=50,
        model="gpt-4o",
        workflow_id="wf-abc",
    )
    rows = await tracker.all_records()
    assert len(rows) == 1
    assert rows[0].workflow_id == "wf-abc"
    assert rows[0].tenant_id == "ws1"


@pytest.mark.asyncio
async def test_record_omits_workflow_id_when_not_provided():
    """Backward compatibility — existing callers (chat runs, etc.)
    must continue to work with no workflow_id."""
    tracker = InMemoryUsageTracker()
    await tracker.record(
        tenant_id="ws1",
        user_id="u1",
        tokens=10,
        model="gpt-4o",
    )
    rows = await tracker.all_records()
    assert rows[0].workflow_id is None


@pytest.mark.asyncio
async def test_usage_record_dataclass_accepts_workflow_id():
    """The dataclass itself carries the optional field — caught at
    import time so callers can't accidentally pass it as positional."""
    record = UsageRecord(
        tenant_id="ws1",
        user_id="u1",
        model="gpt-4o",
        tokens=42,
        timestamp=1700000000.0,
        workflow_id="wf-1",
    )
    assert record.workflow_id == "wf-1"


@pytest.mark.asyncio
async def test_tokens_in_window_filters_by_workflow_id():
    tracker = InMemoryUsageTracker()
    await tracker.record("ws1", "u1", 100, "gpt-4o", workflow_id="wf-a")
    await tracker.record("ws1", "u1", 200, "gpt-4o", workflow_id="wf-b")
    await tracker.record("ws1", "u1", 50, "gpt-4o", workflow_id="wf-a")
    total_a = await tracker.tokens_in_window_for_workflow(
        tenant_id="ws1",
        workflow_id="wf-a",
        window_start=0,
        window_end=float("inf"),
    )
    assert total_a == 150
    total_b = await tracker.tokens_in_window_for_workflow(
        tenant_id="ws1",
        workflow_id="wf-b",
        window_start=0,
        window_end=float("inf"),
    )
    assert total_b == 200


# ---- Router wiring: /execute forwards workflow_id into the tracker ----


def test_router_execute_records_usage_with_workflow_id(monkeypatch):
    """The canvas /execute route must stamp workflow_id on the
    UsageRecord so a quota audit can attribute consumption. We patch
    QuotaService.record_usage so we don't need a real LLM behind the
    executor — the assertion is on the workflow_id that flows in."""
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    qservice = _quota_service()
    configure(wstore, VersionManager(wstore, vstore), quota_service=qservice)

    # Replace the executor with a no-op so /execute returns 200
    # without needing real agent/tool plumbing.
    from app.gateway.canvas.executor import WorkflowExecution
    from app.gateway.canvas.models import WorkflowStatus

    class _NoopExecutor:
        async def execute(self, workflow, inputs):
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            return WorkflowExecution(
                workflow_id=workflow.id,
                workflow_version=workflow.version,
                started_at=now,
                ended_at=now,
                steps=(),
                outputs={},
                total_tokens=120,
                failed_node_id=None,
            )

    from app.gateway.canvas.routers import workflows as wf_router

    wf_router._executor = _NoopExecutor()  # type: ignore[assignment]

    captured: dict[str, str] = {}

    async def fake_record_usage(
        self,
        tokens,
        model,
        tenant_id=None,
        user_id=None,
        workflow_id=None,
    ):
        captured["workflow_id"] = workflow_id or ""
        captured["tenant_id"] = tenant_id or ""
        captured["user_id"] = user_id or ""
        captured["tokens"] = tokens
        return None

    monkeypatch.setattr(
        QuotaService,
        "record_usage",
        fake_record_usage,
    )

    client = _client_with_owner()
    created = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws1",
            "nodes": [{"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}],
            "edges": [],
        },
    ).json()

    resp = client.post(
        f"/api/workflows/{created['id']}/execute",
        json={"inputs": {}, "workspace_id": "ws1", "estimated_tokens": 50},
    )
    assert resp.status_code == 200, resp.text
    assert captured["workflow_id"] == created["id"]
    assert captured["tenant_id"] == "ws1"
    assert captured["user_id"] == "owner"
    assert captured["tokens"] == 120  # executor mock returns 120 tokens
    # Sanity: status field on create response exists.
    assert created["status"] in {s.value for s in WorkflowStatus}
