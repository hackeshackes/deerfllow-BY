"""Integration test for ABAC-gated admin token-usage endpoint (v1.7 M2.4).

Verifies that wiring ``require_abac("read", "admin-token-usage")`` onto
``/api/admin/token-usage`` enforces owner-only (member → 403, owner → 200)
using the built-in policy fallback — the "universal route coverage" pattern.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user


def _make_user(id: str, role: str) -> AuthUser:
    return AuthUser(
        id=id,
        email=f"{id}@x.com",
        role=role,
        name=id,
        status="active",
        password_hash="x",
        salt="y",
    )


@pytest.fixture
def client():
    from app.gateway.routers import admin_token_usage

    app = FastAPI()
    app.include_router(admin_token_usage.router)
    with TestClient(app) as tc:
        yield tc


def _impersonate(client: TestClient, role: str) -> None:
    """Override require_user so requests act as the given role."""
    app: FastAPI = client.app
    app.dependency_overrides[require_user] = lambda: _make_user("u1", role)


def test_member_denied(client: TestClient):
    _impersonate(client, "member")
    resp = client.get("/api/admin/token-usage")
    assert resp.status_code == 403


def test_owner_allowed(client: TestClient, monkeypatch):
    _impersonate(client, "owner")
    # Stub the store so the handler only really exercises the ABAC gate.
    class FakeStore:
        def total(self, since):  # noqa: ANN001
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}

        def aggregate_by_user(self, since):  # noqa: ANN001
            return {}

        def aggregate_by_model(self, since):  # noqa: ANN001
            return {}

    monkeypatch.setattr("deerflow.admin.token_usage.get_token_usage_store", lambda: FakeStore())
    resp = client.get("/api/admin/token-usage")
    assert resp.status_code == 200
    assert resp.json()["total"] == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "request_count": 0,
    }