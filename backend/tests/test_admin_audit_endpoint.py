"""Admin audit query endpoint tests for v1.6.2 admin secrets M2.3.

The admin audit log lives at ``backend/.deer-flow/admin/audit.jsonl`` and
is distinct from the identity audit SQLite store. This file locks the
read surface: owner-only, action_prefix filter, actor_id filter, no
plaintext leakage in the response.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets as _pysecrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser
from app.gateway.routers import admin_secrets
from deerflow.config.paths import Paths


def _gen_str(length: int = 48) -> str:
    return _pysecrets.token_urlsafe(length)


def _fresh_cipher_key() -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(_gen_str(48).encode()).digest()).decode()


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


def _patch_paths(monkeypatch, tmp_path):
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr("deerflow.admin.secrets.get_paths", lambda: paths)
    monkeypatch.setattr("deerflow.admin.audit.get_paths", lambda: paths)
    return paths


@pytest.fixture
def vault_env(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())
    admin_pw = _gen_str(24)
    monkeypatch.setenv("BY_ADMIN_PASSWORD", admin_pw)
    _real_authenticate = admin_secrets.authenticate_user

    def _fake_authenticate(email, password):  # type: ignore[no-untyped-def]
        if password == os.getenv("BY_ADMIN_PASSWORD") and email == os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com"):
            return _owner()
        return _real_authenticate(email, password)

    monkeypatch.setattr(admin_secrets, "authenticate_user", _fake_authenticate)
    return tmp_path


@pytest.fixture
def client(vault_env):
    app = FastAPI()
    app.include_router(admin_secrets.router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_audit_endpoint_lists_admin_secret_events(client, vault_env):
    """Two upserts + one rotate should produce three records; the
    endpoint returns them in newest-first order with ``action_prefix``
    filter applied.
    """
    new_value = _gen_str(40)
    r1 = client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/x/api_key", "value": _gen_str(20)},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/y/api_key", "value": _gen_str(20)},
    )
    assert r2.status_code == 200
    r3 = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": new_value,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r3.status_code == 200

    r = client.get("/api/admin/secrets/audit-events?action_prefix=admin_secret.")
    assert r.status_code == 200
    body = r.json()
    actions = [e["action"] for e in body["events"]]
    assert "admin_secret.upserted" in actions
    assert "admin_secret.rotated" in actions


def test_audit_endpoint_never_returns_plaintext_secret(client, vault_env):
    sensitive = _gen_str(40)
    client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": sensitive,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    r = client.get("/api/admin/secrets/audit-events?action_prefix=admin_secret.")
    body = r.json()
    serialized = json.dumps(body)
    assert sensitive not in serialized
    # The audit records ``value_length`` only.
    for event in body["events"]:
        if event["action"] == "admin_secret.rotated":
            assert event["details"].get("value_length") == len(sensitive)


def test_audit_endpoint_filters_by_actor(client, vault_env):
    """``actor_id`` filter pins events to one owner."""
    client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/x/api_key", "value": _gen_str(20)},
    )
    r = client.get(
        "/api/admin/secrets/audit-events?action_prefix=admin_secret.&actor_id=owner",
    )
    assert r.status_code == 200
    for event in r.json()["events"]:
        assert event["actor_id"] == "owner"


def test_audit_endpoint_rejects_non_owner(client, vault_env, monkeypatch):
    from unittest.mock import patch

    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        r = client.get("/api/admin/secrets/audit-events?action_prefix=admin_secret.")
    assert r.status_code == 403


def test_audit_endpoint_empty_when_no_events(client, vault_env):
    r = client.get("/api/admin/secrets/audit-events")
    assert r.status_code == 200
    assert r.json()["events"] == []