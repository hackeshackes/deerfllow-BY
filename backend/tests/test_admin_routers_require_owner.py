"""V02 + V07 — Router-level owner-only enforcement tests.

Each admin router (``audit``, ``rbac``, ``scim``) declares
``Depends(require_owner_user)`` at the router level. These tests verify
that ``require_owner_user`` raises 403 when the resolved user is not an
owner, and lets owners through.

Test strategy
=============

``require_owner_user`` ultimately calls ``session_user_from_request``,
which has a deliberate pytest-only escape hatch that auto-seeds the owner
when ``PYTEST_CURRENT_TEST`` is set. To exercise the member path we patch
that helper to return a member and call ``require_owner_user`` with a stub
request — this directly verifies the owner check at the source of truth,
which is what the router middleware delegates to.

We also mount the three routers on an isolated ``FastAPI`` app and verify
that ``Depends(require_owner_user)`` wired at the router level actually
rejects requests when the underlying dependency raises HTTP 403 — this
exercises the integration without depending on cookie signing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, HTTPException, require_owner_user


# ---------------------------------------------------------------------------
# Fixtures: owner + member users
# ---------------------------------------------------------------------------


def _owner() -> AuthUser:
    return AuthUser(
        id="owner-1",
        email="sabar.bao@me.com",
        role="owner",
        name="MicX Owner",
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


class _StubRequest:
    """Minimal Request stand-in for unit-testing ``require_owner_user``."""

    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Unit tests — verify require_owner_user itself enforces the policy
# ---------------------------------------------------------------------------


def test_require_owner_user_rejects_member() -> None:
    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        with pytest.raises(HTTPException) as excinfo:
            require_owner_user(_StubRequest())
    assert excinfo.value.status_code == 403
    # The detail string is the i18n message that ships with auth.py
    # (``"仅拥有者可执行此操作"``). Assert the HTTP status alone to keep this
    # test independent of the message wording.
    assert excinfo.value.detail


def test_require_owner_user_accepts_owner() -> None:
    with patch("app.gateway.auth.session_user_from_request", return_value=_owner()):
        result = require_owner_user(_StubRequest())
    assert result.is_owner is True
    assert result.role == "owner"


def test_require_owner_user_rejects_anonymous() -> None:
    with patch("app.gateway.auth.session_user_from_request", return_value=None):
        with pytest.raises(HTTPException) as excinfo:
            require_owner_user(_StubRequest())
    assert excinfo.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests — verify routers actually mount the dependency
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_app() -> Any:
    """Build a minimal FastAPI app that mounts the three admin routers."""
    from app.gateway.identity.routers.audit import router as audit_router
    from app.gateway.identity.routers.rbac import router as rbac_router
    from app.gateway.identity.routers.scim import router as scim_router

    app = FastAPI()
    app.include_router(audit_router)
    app.include_router(rbac_router)
    app.include_router(scim_router)
    yield app
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("get", "/api/admin/audit/events", None),
        ("get", "/api/admin/audit/export", None),
        ("get", "/api/admin/roles", None),
        ("get", "/api/admin/scim/state", None),
        ("post", "/api/admin/scim/sync/prov1", None),
        ("put", "/api/admin/scim/state/prov1", {"enabled": True}),
    ],
)
def test_admin_routers_reject_member(
    admin_app: FastAPI, method: str, path: str, body: dict | None
) -> None:
    """Patch the session resolver to return a member; the router-level
    ``Depends(require_owner_user)`` must convert that into 403.
    """
    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        client = TestClient(admin_app, raise_server_exceptions=False)
        kwargs = {"json": body} if body is not None else {}
        response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403, f"{method.upper()} {path} → {response.status_code} {response.text}"


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/admin/audit/events"),
        ("get", "/api/admin/audit/export"),
        ("get", "/api/admin/roles"),
        ("get", "/api/admin/scim/state"),
    ],
)
def test_admin_routers_accept_owner(admin_app: FastAPI, method: str, path: str) -> None:
    with patch("app.gateway.auth.session_user_from_request", return_value=_owner()):
        client = TestClient(admin_app, raise_server_exceptions=False)
        response = getattr(client, method)(path)
    # 5xx from the handler would mean the owner passed the gate; the handler
    # itself may legitimately return 4xx/200 depending on the test environment.
    assert response.status_code != 401
    assert response.status_code != 403, f"{method.upper()} {path} → {response.status_code} {response.text}"