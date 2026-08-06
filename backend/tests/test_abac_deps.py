"""Unit tests for the reusable ABAC gating dependency (v1.7 M2.4).

``abac/deps.py`` exposes ``require_abac(action, resource_type, workspace_id='')``
— a FastAPI dependency factory that builds a Subject from the authenticated
user (plus its workspace memberships), a Resource from request context, and
evaluates the resolved policy set (loader or built-in fallback). Verdicts:
allow → pass; deny / no-match → 403 (fail-closed).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.gateway.abac.deps import require_abac
from app.gateway.auth import AuthUser, require_user


def _override_user(role: str):

    def _override() -> AuthUser:
        return AuthUser(
            id="u1",
            email="u@x.com",
            role=role,
            name="U",
            status="active",
            password_hash="x",
            salt="y",
        )

    return _override


def _stub_memberships(monkeypatch, workspace_ids: list[str]) -> None:
    """Mock the registry lookup that feeds the ABAC Subject."""
    class _Rec:
        def __init__(self, workspace_id: str) -> None:
            self.workspace_id = workspace_id

    monkeypatch.setattr(
        "app.gateway.abac.deps.list_workspaces_for_user",
        lambda _uid: [_Rec(w) for w in workspace_ids],
    )


def _app(*, action: str, resource_type: str, workspace_id: str = ""):
    app = FastAPI()

    @app.get("/gate")
    def gate(user: AuthUser = Depends(require_abac(action, resource_type, workspace_id))):
        return {"ok": True}

    return app


def test_owner_allowed_owner_only_action():
    app = _app(action="publish", resource_type="thread")
    app.dependency_overrides[require_user] = _override_user("owner")
    with TestClient(app) as client:
        assert client.get("/gate").status_code == 200


def test_member_denied_owner_only_action():
    app = _app(action="publish", resource_type="thread")
    app.dependency_overrides[require_user] = _override_user("member")
    with TestClient(app) as client:
        assert client.get("/gate").status_code == 403


def test_member_allowed_when_workspace_matches(monkeypatch):
    _stub_memberships(monkeypatch, workspace_ids=["ws-1"])
    app = _app(action="execute", resource_type="workflow", workspace_id="ws-1")
    app.dependency_overrides[require_user] = _override_user("member")
    with TestClient(app) as client:
        assert client.get("/gate").status_code == 200


def test_member_denied_when_workspace_mismatches(monkeypatch):
    _stub_memberships(monkeypatch, workspace_ids=["ws-other"])
    app = _app(action="execute", resource_type="workflow", workspace_id="ws-1")
    app.dependency_overrides[require_user] = _override_user("member")
    with TestClient(app) as client:
        assert client.get("/gate").status_code == 403