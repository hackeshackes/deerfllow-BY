"""Tests for the owner-only admin ABAC policies API (v1.7 M2.6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.routers import admin_policies


def _make_user(role: str) -> AuthUser:
    return AuthUser(
        id="u1",
        email="u@x.com",
        role=role,
        name="U",
        status="active",
        password_hash="x",
        salt="y",
    )


@pytest.fixture
def client(tmp_path: Path):
    admin_policies.configure_policies_file(str(tmp_path / "policies.json"))
    app = FastAPI()
    app.include_router(admin_policies.router)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_path():
    yield
    admin_policies.configure_policies_file(None)


def _impersonate(client: TestClient, role: str) -> None:
    client.app.dependency_overrides[require_user] = lambda: _make_user(role)


def test_member_cannot_read(client: TestClient):
    _impersonate(client, "member")
    resp = client.get("/api/admin/policies")
    assert resp.status_code == 403


def test_owner_reads_builtin_presets(client: TestClient):
    _impersonate(client, "owner")
    resp = client.get("/api/admin/policies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 1
    ids = [p["id"] for p in body["policies"]]
    assert "owner-only" in ids


def test_owner_put_valid_policy(client: TestClient, tmp_path: Path):
    _impersonate(client, "owner")
    payload = {
        "version": 1,
        "policies": [
            {
                "id": "ban-everything",
                "effect": "deny",
                "combiner": "any_of",
                "conditions": [],
            }
        ],
    }
    resp = client.put("/api/admin/policies", json=payload)
    assert resp.status_code == 200, resp.text
    assert (tmp_path / "policies.json").exists()
    assert "ban-everything" in (tmp_path / "policies.json").read_text()


def test_owner_put_invalid_policy_rejected(client: TestClient, tmp_path: Path):
    _impersonate(client, "owner")
    payload = {"version": 1, "policies": [{"id": "bad", "effect": "maybe"}]}
    resp = client.put("/api/admin/policies", json=payload)
    assert resp.status_code == 400
    # Nothing was written.
    assert not (tmp_path / "policies.json").exists()


def test_put_without_configured_path_503(client: TestClient):
    admin_policies.configure_policies_file(None)
    _impersonate(client, "owner")
    payload = {"version": 1, "policies": [{"id": "x", "effect": "allow", "conditions": []}]}
    resp = client.put("/api/admin/policies", json=payload)
    assert resp.status_code == 503