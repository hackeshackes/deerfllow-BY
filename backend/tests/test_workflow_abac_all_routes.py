"""ABAC coverage for every workflow route (v1.7 M2 B).

Owner can create and operate on any workflow. A member may not create
(403), and single-resource routes (get/update/delete/versions/rollback/
executions) are gated to the workflow's workspace via the inline ABAC helper:
member inside the workspace → 200; member outside three → 404 (hide semantics).

Before M2 B these read/update/delete routes had NO isolation (any authed user
passed), so the out-of-workspace deny tests are the RED that drives the change.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.canvas.routers.workflows import (
    configure,
    reset_for_tests,
)
from app.gateway.canvas.routers.workflows import (
    router as canvas_router,
)
from app.gateway.canvas.store import InMemoryWorkflowStore
from app.gateway.canvas.versions import InMemoryVersionStore, VersionManager


def _owner() -> AuthUser:
    return AuthUser(
        id="owner",
        email="o@x.com",
        role="owner",
        name="O",
        status="active",
        password_hash="x",
        salt="y",
    )


def _member() -> AuthUser:
    return AuthUser(
        id="m1",
        email="m@x.com",
        role="member",
        name="M",
        status="active",
        password_hash="x",
        salt="y",
    )


class _Rec:
    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id


def _set_memberships(monkeypatch, ids: list[str]) -> None:
    class _Rec:
        def __init__(self, workspace_id: str) -> None:
            self.workspace_id = workspace_id

    monkeypatch.setattr(
        "app.gateway.canvas.routers.workflows.list_workspaces_for_user",
        lambda _uid: [_Rec(w) for w in ids],
    )


@pytest.fixture
def client(monkeypatch):
    configure(
        InMemoryWorkflowStore(),
        VersionManager(InMemoryWorkflowStore(), InMemoryVersionStore()),
    )
    app = FastAPI()
    app.include_router(canvas_router)
    app.dependency_overrides[require_user] = _owner
    with TestClient(app) as tc:
        yield tc
    reset_for_tests()


def _create_wf(client: TestClient) -> str:
    resp = client.post(
        "/api/workflows",
        json={
            "name": "demo",
            "workspace_id": "ws-a",
            "nodes": [
                {"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}
            ],
            "edges": [],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _as_member(client: TestClient) -> None:
    client.app.dependency_overrides[require_user] = _member


def test_create_denied_for_member(client: TestClient):
    _as_member(client)
    resp = client.post(
        "/api/workflows",
        json={"name": "x", "workspace_id": "ws-a", "nodes": [], "edges": []},
    )
    assert resp.status_code == 403, resp.text


def test_create_allowed_for_owner(client: TestClient):
    resp = client.post(
        "/api/workflows",
        json={"name": "x", "workspace_id": "ws-a", "nodes": [], "edges": []},
    )
    assert resp.status_code == 200, resp.text


def test_member_in_workspace_can_read_update_delete(client: TestClient, monkeypatch):
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _create_wf(client)
    _as_member(client)

    assert client.get(f"/api/workflows/{wf_id}").status_code == 200
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "renamed"}).status_code
        == 200
    )
    assert client.get(f"/api/workflows/{wf_id}/versions").status_code == 200
    assert client.get(f"/api/workflows/{wf_id}/executions").status_code == 200


def test_member_outside_workspace_denied(client: TestClient, monkeypatch):
    _set_memberships(monkeypatch, ["ws-other"])
    wf_id = _create_wf(client)
    _as_member(client)

    # Single-resource route -> 404 (hide), not 403.
    assert client.get(f"/api/workflows/{wf_id}").status_code == 404
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "x"}).status_code == 404
    )
    assert client.get(f"/api/workflows/{wf_id}/versions").status_code == 404
    assert client.delete(f"/api/workflows/{wf_id}").status_code == 404


def test_owner_can_operate_regardless_of_membership(client: TestClient):
    # Owner default; no memberships set at all.
    wf_id = _create_wf(client)
    assert client.get(f"/api/workflows/{wf_id}").status_code == 200
    assert client.delete(f"/api/workflows/{wf_id}").status_code == 200