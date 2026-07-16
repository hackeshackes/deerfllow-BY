"""SECRETS_VAULT_ROUTABLE allow-list tests for v1.6.2 admin secrets M2.2.

Only keys explicitly listed in ``SECRETS_VAULT_ROUTABLE`` can be rotated
through the ``/api/admin/secrets/rotate`` endpoint. Everything else must
be rotated by editing ``.env`` and restarting — keeps MCP-injected vendor
keys out of the vault rotation path where the cipher swap doesn't apply.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets as _pysecrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser
from app.gateway.routers import admin_secrets
from deerflow.admin import SECRETS_VAULT_ROUTABLE
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


def _patch_paths(monkeypatch, tmp_path):
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr("deerflow.admin.secrets.get_paths", lambda: paths)
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


def test_allowlist_includes_privileged_and_production_vault_keys():
    # The two privileged keys — cipher rotation relies on these.
    assert "BETTER_AUTH_SECRET" in SECRETS_VAULT_ROUTABLE
    assert "MICX_ADMIN_SECRET_KEY" in SECRETS_VAULT_ROUTABLE
    # Every catalog vault key must be rotatable, otherwise operators
    # can't roll credentials after the M1 router shipped.
    for key in (
        "models/dspark-v1.1-mida-brikie/api_key",
        "models/mixh-coder/api_key",
        "models/Qwen3-5-35B-A3B-Claude-4-6-Opus-Reasoning/api_key",
        "models/MicX Service/api_key",
    ):
        assert key in SECRETS_VAULT_ROUTABLE, f"missing {key}"


def test_allowlist_excludes_env_only_vendor_keys():
    # Vendor API keys live in env (env-routed) and shouldn't be rotated
    # via the vault endpoint — they'd need a cipher swap for no benefit.
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TAVILY_API_KEY"):
        assert key not in SECRETS_VAULT_ROUTABLE, f"{key} should be env-only"


def test_allowlist_excludes_placeholder_keys():
    # The local placeholder is for cold-start; never a real key to rotate.
    assert "models/local-openai-placeholder/api_key" not in SECRETS_VAULT_ROUTABLE


def test_rotate_rejects_non_routable_key(client, vault_env):
    """``OPENAI_API_KEY`` is not in the allow-list; the router must
    refuse it with 400 rather than silently running the cipher swap
    (which wouldn't apply — env-only key has no vault entry) or
    upserting a vault entry under that name (operator surprise).
    """
    r = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "OPENAI_API_KEY",
            "new_value": _gen_str(40),
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert "not rotatable" in body["detail"]
    # Must mention editing .env so the operator knows the escape hatch.
    assert ".env" in body["detail"]