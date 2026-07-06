from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser
from app.gateway.canvas.routers.workflows import (
    configure,
    reset_for_tests,
)
from app.gateway.canvas.routers.workflows import (
    router as canvas_router,
)
from app.gateway.canvas.store import InMemoryWorkflowStore
from app.gateway.canvas.versions import InMemoryVersionStore, VersionManager


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


def _owner() -> AuthUser:
    return AuthUser(
        id="owner",
        email="sabar.bao@me.com",
        role="owner",
        name="MicX Owner",
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


def test_post_workflow_increments_version_and_returns_workflow():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    configure(wstore, VersionManager(wstore, vstore))

    client = _client_with_owner()
    resp = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws1",
            "nodes": [{"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}],
            "edges": [],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["workspace_id"] == "ws1"


def test_put_workflow_increments_version_and_commits_version():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    configure(wstore, VersionManager(wstore, vstore))

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
    assert created["version"] == 1

    updated = client.put(
        f"/api/workflows/{created['id']}",
        json={"name": "demo2"},
    ).json()
    assert updated["version"] == 2
    assert updated["name"] == "demo2"

    versions = client.get(f"/api/workflows/{created['id']}/versions").json()
    assert len(versions["versions"]) == 2


def test_post_without_workspace_id_returns_422():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    configure(wstore, VersionManager(wstore, vstore))

    client = _client_with_owner()
    resp = client.post("/api/workflows", json={"name": "demo"})
    assert resp.status_code == 422
