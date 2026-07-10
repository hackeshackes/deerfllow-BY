"""ABAC integration tests for the canvas /execute route (v1.6.1).

Verifies that ABAC denies a non-owner, non-workspace-member from
running a workflow — the check fires before the executor (matches
the existing pre-execute authorization behavior).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.canvas.routers.workflows import (
    configure,
    reset_for_tests,
    router as canvas_router,
)
from app.gateway.canvas.store import InMemoryWorkflowStore
from app.gateway.canvas.versions import InMemoryVersionStore, VersionManager


def _owner():
    return AuthUser(
        id="u1",
        email="o@x.com",
        role="owner",
        name="O",
        status="active",
        password_hash="x",
        salt="y",
    )


def _member_no_workspaces():
    return AuthUser(
        id="u2",
        email="m@x.com",
        role="member",  # not owner → WorkspaceMemberPolicy must carry it
        name="M",
        status="active",
        password_hash="x",
        salt="y",
    )


def test_abac_denies_member_with_no_workspace_membership_from_executing():
    """A 'member' user without workspace membership is denied by ABAC
    before the executor is invoked (so no 503, no usage record).
    """
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    configure(wstore, VersionManager(wstore, vstore))

    # Owner creates the workflow.
    app = FastAPI()
    app.include_router(canvas_router)
    app.dependency_overrides[require_user] = _owner
    client = TestClient(app)

    created = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws-a",
            "nodes": [
                {"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}
            ],
            "edges": [],
        },
    ).json()

    # Now switch to a member identity and try to execute.
    app.dependency_overrides[require_user] = _member_no_workspaces

    resp = client.post(
        f"/api/workflows/{created['id']}/execute",
        json={"inputs": {}, "workspace_id": "ws-a", "estimated_tokens": 10},
    )
    assert resp.status_code == 403, resp.text
    assert "no matching policy" in resp.text
    reset_for_tests()


def test_abac_allows_owner_to_execute_despite_no_workspace_membership():
    """OwnerOnlyPolicy bypasses the workspace list check — even with
    no memberships, an owner can run any workflow they can reach."""
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    configure(wstore, VersionManager(wstore, vstore))

    app = FastAPI()
    app.include_router(canvas_router)
    app.dependency_overrides[require_user] = _owner
    client = TestClient(app)

    created = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws-a",
            "nodes": [
                {"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}
            ],
            "edges": [],
        },
    ).json()

    # No executor configured → 503 (the ABAC allowed pass). What we
    # care about is the *pre-execute* 403 didn't fire. Adding an
    # executor here would make the test brittle; the deny-path test
    # above already pins the ABAC-on-deny behavior.
    resp = client.post(
        f"/api/workflows/{created['id']}/execute",
        json={"inputs": {}, "workspace_id": "ws-a", "estimated_tokens": 10},
    )
    assert resp.status_code == 503, resp.text  # no executor → not 403
    reset_for_tests()
