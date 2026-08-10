"""Workflow ABAC authorization matrix (v1.7 M2 B).

Single-resource routes (get/update/delete/versions/rollback/executions)
are workspace-isolated via ``_authorize_workflow`` + ``_require_single_workflow``:
owner bypasses (OwnerOnlyPolicy), a member is allowed only when the
workflow's ``workspace_id`` is in ``list_workspaces_for_user``. On deny the
single-resource helper hides the workflow with a generic 404.

This matrix pins the exact boundary semantics so the authorization surface
does not drift:
  * member in ws-a on a ws-a workflow  -> 200 for read/write/versions/executions
  * member with ws-b on a ws-a workflow -> 404 everywhere (hide, not 403)
  * member with NO workspaces          -> 404
  * owner with NO memberships          -> 200 (owner-only short-circuits)
  * member must NOT create             -> 403 (require_abac gate, fail-closed)
  * member out-of-ws execute           -> 403 (execute keeps its legacy 403,
                                            never silently 404-hides)
  * rollback to missing version        -> 404 (LookupError path); for a
                                            non-member the generic 404 hides
                                            the workflow id (no leak)
  * list_workflows trusts workspace_id -> member can enumerate workflows from
    a workspace they are not a member of (authorization gap)
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser
from app.gateway.canvas.executor import WorkflowExecutor
from app.gateway.canvas.models import NodeKind
from app.gateway.canvas.nodes.prompt import PromptNode
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
        id="owner", email="owner@x.com", role="owner",
        name="O", status="active", password_hash="x", salt="y",
    )


def _member(member_id: str = "m1") -> AuthUser:
    return AuthUser(
        id=member_id, email=f"{member_id}@x.com", role="member",
        name="M", status="active", password_hash="x", salt="y",
    )


def _set_memberships(monkeypatch, ids: list[str]) -> None:
    """Seed ``list_workspaces_for_user`` for the workflows router module."""
    class _Rec:
        def __init__(self, workspace_id: str):
            self.workspace_id = workspace_id

    monkeypatch.setattr(
        "app.gateway.canvas.routers.workflows.list_workspaces_for_user",
        lambda _uid: [_Rec(w) for w in ids],
    )


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    reset_for_tests()


def _rig(monkeypatch, *, executor=None):
    """Build one app+store; monkeypatch the router's list_workspaces_for_user
    so its value is observable, and return a (client, switch_user) pair.

    NOTE: we override the router module's OWN ``require_user`` binding (not the
    test's import-time ``app.gateway.auth.require_user``) so the override key
    survives an ``importlib.reload`` of ``app.gateway.auth`` by an earlier suite
    test. Same fix as the collab-publish isolation (v1.7 M1).
    """
    import app.gateway.canvas.routers.workflows as wfmod

    w = InMemoryWorkflowStore()
    v = InMemoryVersionStore()
    configure(w, VersionManager(w, v), executor=executor)

    current = {"user": _owner()}

    def _as_user():
        return current["user"]

    app = FastAPI()
    app.include_router(canvas_router)
    app.dependency_overrides[wfmod.require_user] = _as_user

    def switch(user: AuthUser) -> None:
        current["user"] = user

    client = TestClient(app)
    return client, switch


def _seed_wf(client: TestClient, workspace_id: str = "ws-a") -> str:
    """Create a workflow as the currently-authed (owner) user; return id."""
    resp = client.post(
        "/api/workflows",
        json={"name": "demo", "workspace_id": workspace_id, "nodes": [], "edges": []},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------- member in-ws -> 200


def test_member_in_workspace_get_update_versions_executions(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])  # applies to owner+member alike
    wf_id = _seed_wf(client)

    switch(_member("m-in"))
    assert client.get(f"/api/workflows/{wf_id}").status_code == 200
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "renamed"}).status_code == 200
    )
    assert client.get(f"/api/workflows/{wf_id}/versions").status_code == 200
    assert client.get(f"/api/workflows/{wf_id}/executions").status_code == 200


# ------------------------------------------------------ out-of-ws -> 404 (hide)


def test_member_out_of_workspace_hides_single_resource_routes(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-out"))
    _set_memberships(monkeypatch, ["ws-b"])
    # All single-resource routes 404 (hide), never 403.
    assert client.get(f"/api/workflows/{wf_id}").status_code == 404
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "x"}).status_code == 404
    )
    assert client.get(f"/api/workflows/{wf_id}/versions").status_code == 404
    assert client.delete(f"/api/workflows/{wf_id}").status_code == 404
    assert client.get(f"/api/workflows/{wf_id}/executions").status_code == 404


# -------------------------------------------------------- no workspaces -> 404


def test_member_with_no_workspaces_hides(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-none"))
    _set_memberships(monkeypatch, [])
    assert client.get(f"/api/workflows/{wf_id}").status_code == 404
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "x"}).status_code == 404
    )
    assert client.delete(f"/api/workflows/{wf_id}").status_code == 404
    assert client.get(f"/api/workflows/{wf_id}/executions").status_code == 404


# ----------------------------------------------- owner no-membership -> 200


def test_owner_with_no_memberships_can_operate(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, [])  # owner has zero memberships
    wf_id = _seed_wf(client)
    switch(_owner())

    # OwnerOnlyPolicy short-circuits -> 200 even with no memberships.
    assert client.get(f"/api/workflows/{wf_id}").status_code == 200
    assert client.get(f"/api/workflows/{wf_id}/versions").status_code == 200
    assert client.get(f"/api/workflows/{wf_id}/executions").status_code == 200
    assert (
        client.put(f"/api/workflows/{wf_id}", json={"name": "by-owner"}).status_code == 200
    )
    assert client.post(f"/api/workflows/{wf_id}/rollback/1").status_code == 200


# --------------------------------------------------------------- create 403 --


def test_member_cannot_create(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    switch(_member("m-c"))
    # Even a member OF the workspace is denied create (OwnerOnly action).
    resp = client.post(
        "/api/workflows",
        json={"name": "x", "workspace_id": "ws-a", "nodes": [], "edges": []},
    )
    assert resp.status_code == 403, resp.text


def test_owner_can_create(monkeypatch):
    client, _switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, [])
    resp = client.post(
        "/api/workflows",
        json={"name": "x", "workspace_id": "ws-a", "nodes": [], "edges": []},
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------- execute ----


def test_execute_member_out_of_workspace_is_403(monkeypatch):
    """Execute keeps its inline 403, NOT a 404-hide. A 404 would claim the
    workflow vanishes; execute intentionally surfaces 403 (body-ws guard +
    ABAC) consistent with its pre-M2B behavior.
    """
    executor = WorkflowExecutor(node_executors={NodeKind.PROMPT: PromptNode()})
    client, switch = _rig(monkeypatch, executor=executor)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-e"))
    _set_memberships(monkeypatch, ["ws-b"])
    resp = client.post(
        f"/api/workflows/{wf_id}/execute",
        json={"inputs": {}, "workspace_id": "ws-a", "estimated_tokens": 1},
    )
    assert resp.status_code == 403, resp.text


def test_execute_member_in_workspace_allowed(monkeypatch):
    executor = WorkflowExecutor(node_executors={NodeKind.PROMPT: PromptNode()})
    client, switch = _rig(monkeypatch, executor=executor)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-e2"))
    resp = client.post(
        f"/api/workflows/{wf_id}/execute",
        json={"inputs": {}, "workspace_id": "ws-a", "estimated_tokens": 1},
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------- rollback ---


def test_rollback_missing_version_member_in_ws_is_404(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-r"))
    resp = client.post(f"/api/workflows/{wf_id}/rollback/99")
    # Authorized (in-ws) member, but version missing -> 404, NOT 403.
    assert resp.status_code == 404, resp.text


def test_rollback_missing_version_out_of_ws_hides_id(monkeypatch):
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-r2"))
    _set_memberships(monkeypatch, ["ws-b"])
    resp = client.post(f"/api/workflows/{wf_id}/rollback/999")
    # Non-member: _require_single_workflow fires first -> generic 404 that must
    # NOT contain the workflow id (the version-manager LookupError detail
    # "version 999 not found for workflow {id}" WOULD leak it if reached).
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == "workflow not found"
    assert str(wf_id) not in resp.text


def test_rollback_missing_version_in_ws_does_leak_wf_id(monkeypatch):
    """Contrast to the hide case: an AUTHORIZED (in-ws) member who hits a
    missing version gets the version-manager LookupError detail, which
    includes the workflow id. This is acceptable (they can see the workflow
    anyway) but confirms the difference between the two 404 paths."""
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    wf_id = _seed_wf(client)

    switch(_member("m-r3"))
    resp = client.post(f"/api/workflows/{wf_id}/rollback/987")
    assert resp.status_code == 404, resp.text
    assert str(wf_id) in resp.text  # LookupError detail mentions the id


def test_rollback_missing_version_owner_is_404(monkeypatch):
    client, _switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, [])
    wf_id = _seed_wf(client)
    resp = client.post(f"/api/workflows/{wf_id}/rollback/999")
    assert resp.status_code == 404, resp.text


# ----------------------------------------------------------- list scoping ----


def test_list_workflows_member_cannot_list_unjoined_workspace(monkeypatch):
    """v1.7 M2 B regression: list_workflows must NOT leak another workspace's
    workflows. A member who only belongs to ws-a must be denied (403) when
    querying workspace_id=ws-b, rather than seeing its workflows.
    """
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    _seed_wf(client, workspace_id="ws-b")  # a ws-b workflow

    switch(_member("m-list"))
    resp = client.get("/api/workflows", params={"workspace_id": "ws-b"})
    assert resp.status_code == 403, resp.text


def test_list_workflows_member_sees_only_lists_scoped_ws(monkeypatch):
    """Sanity: when the member queries their OWN workspace the listing returns
    that workspace's workflows (and not a cross-ws batch)."""
    client, switch = _rig(monkeypatch)
    _set_memberships(monkeypatch, ["ws-a"])
    mine = _seed_wf(client, workspace_id="ws-a")

    switch(_member("m-l2"))
    resp = client.get("/api/workflows", params={"workspace_id": "ws-a"})
    assert resp.status_code == 200, resp.text
    wf_ids = {item["id"] for item in resp.json()["workflows"]}
    assert mine in wf_ids