"""ABAC coverage for the legacy owner-only admin routers (v1.7 M2.8).

Each of these five routers gates its handlers imperatively via
``require_owner_user(request)`` today; this test asserts the ABAC gate
(``require_abac(verb, resource_type)``) delivers the same owner-only
semantics once they're converted:

* owner  -> allowed (assert result is NOT 401 / NOT 403; the handler may
            legitimately 5xx or 200 in isolation -- the gate is what we verify)
* member -> 403 (ABAC raises before the handler body, so no handler setup
            is required for the denial path)

A dedicated case locks in that a member who *does* belong to a workspace is
still denied: admin routes pass an empty ``workspace_id``, so the
WorkspaceMemberPolicy member branch (``"" in subject.workspaces``) never
matches. Only the owner branch of the built-in fallback applies.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser
from app.gateway.routers import (
    admin_config,
    admin_knowledge,
    admin_memory,
    admin_monitoring,
    admin_secrets,
)

# (method, path, stubbed json body or None) exercised against each router.
# Each tuple is (method, path, body); the JSON method name is method.lower().
ROUTE_CASES: list[tuple[Any, str, str, dict | None]] = [
    (admin_config.router, "get", "/api/admin/config", None),
    (admin_config.router, "put", "/api/admin/config", {}),
    (admin_config.router, "get", "/api/admin/config/schema", None),
    (admin_config.router, "post", "/api/admin/config/validate", {}),
    (admin_config.router, "get", "/api/admin/audit", None),
    (admin_knowledge.router, "get", "/api/admin/knowledge", None),
    (admin_knowledge.router, "put", "/api/admin/knowledge/kb1", {}),
    (admin_knowledge.router, "delete", "/api/admin/knowledge/kb1", None),
    (admin_memory.router, "get", "/api/admin/memory/users/u1", None),
    (admin_monitoring.router, "get", "/api/admin/monitoring/overview", None),
    (admin_secrets.router, "post", "/api/admin/secrets/upsert", {"key": "models/foo/api_key"}),
    (
        admin_secrets.router,
        "post",
        "/api/admin/secrets/rotate",
        {"key": "models/foo/api_key", "new_value": "v", "current_admin_password": "p"},
    ),
    (admin_secrets.router, "get", "/api/admin/secrets/status", None),
    (admin_secrets.router, "get", "/api/admin/secrets/audit-events", None),
]


def _owner() -> AuthUser:
    return AuthUser(
        id="owner-1",
        email="owner@example.com",
        role="owner",
        name="Owner",
        status="active",
        password_hash="x",
        salt="y",
    )


def _member() -> AuthUser:
    return AuthUser(
        id="member-1",
        email="member@example.com",
        role="member",
        name="Member",
        status="active",
        password_hash="x",
        salt="y",
    )


def _mount(router: Any) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _request(client: TestClient, method: str, path: str, body: dict | None):
    kwargs = {"json": body} if body is not None else {}
    return getattr(client, method)(path, **kwargs)


@pytest.mark.parametrize(
    ("router", "method", "path", "body"),
    ROUTE_CASES,
)
def test_admin_route_allows_owner(
    router: Any, method: str, path: str, body: dict | None
) -> None:
    app = _mount(router)
    # Stub the rotate endpoint's password re-auth so a valid owner clears the
    # owner-only ABAC gate and reaches/passes the handler's own password check.
    # (In an isolated test the owner isn't in the real user store, so
    # ``_verify_owner_password`` would otherwise raise 401, obscuring the gate.)
    with patch(
        "app.gateway.routers.admin_secrets.authenticate_user", return_value=_owner()
    ), patch(
        "app.gateway.auth.session_user_from_request", return_value=_owner()
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = _request(client, method, path, body)
    assert resp.status_code != 401, f"{method} {path} -> {resp.status_code} {resp.text}"
    assert resp.status_code != 403, f"{method} {path} -> {resp.status_code} {resp.text}"


@pytest.mark.parametrize(
    ("router", "method", "path", "body"),
    ROUTE_CASES,
)
def test_admin_route_denies_member(
    router: Any, method: str, path: str, body: dict | None
) -> None:
    app = _mount(router)
    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = _request(client, method, path, body)
    assert resp.status_code == 403, f"{method} {path} -> {resp.status_code} {resp.text}"


def test_admin_read_denies_workspace_member_with_membership() -> None:
    """A member who belongs to a real workspace is STILL denied on admin
    routes: they carry an empty workspace_id, so the WorkspaceMemberPolicy
    member branch never matches -- admin coverage stays owner-only.
    """
    import app.gateway.abac.deps as abac_deps

    class _Rec:
        def __init__(self, wid: str) -> None:
            self.workspace_id = wid

    app = _mount(admin_config.router)
    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        with patch.object(
            abac_deps, "list_workspaces_for_user", lambda _uid: [_Rec("ws-1")]
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/api/admin/config")
    assert resp.status_code == 403, f"GET /api/admin/config -> {resp.status_code} {resp.text}"