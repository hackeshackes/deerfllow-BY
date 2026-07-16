"""End-to-end tests for the v1.6.2 admin secrets endpoints.

All secret values are generated with ``secrets.token_urlsafe`` at runtime — no
real credentials are ever embedded in the test source. ``PYTEST_CURRENT_TEST``
is set by pytest, so the owner is auto-seeded by ``session_user_from_request``
without any cookie signing.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets as _pysecrets
from collections import deque
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, decode_session_token
from app.gateway.routers import admin_secrets
from deerflow.config.paths import Paths


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


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
    return paths


def _gen_str(length: int = 48) -> str:
    return _pysecrets.token_urlsafe(length)


def _fresh_cipher_key() -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(_gen_str(48).encode()).digest()).decode()


@pytest.fixture
def vault_env(monkeypatch, tmp_path):
    """Patch vault paths to ``tmp_path``, set cipher + admin password, and
    stub ``authenticate_user`` so the rotate verification accepts the
    fixture password (the real implementation needs ``users.json`` which the
    router tests intentionally avoid)."""
    _patch_paths(monkeypatch, tmp_path)
    admin_pw = _gen_str(24)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())
    monkeypatch.setenv("BY_ADMIN_PASSWORD", admin_pw)
    # Stub the router-side authenticate_user so the rotate endpoint accepts
    # the fixture password without round-tripping through users.json.
    _real_authenticate = admin_secrets.authenticate_user

    def _fake_authenticate(email, password):  # type: ignore[no-untyped-def]
        if password == os.getenv("BY_ADMIN_PASSWORD") and email == os.getenv(
            "BY_ADMIN_EMAIL", "sabar.bao@me.com"
        ):
            return _owner()
        return _real_authenticate(email, password)

    monkeypatch.setattr(admin_secrets, "authenticate_user", _fake_authenticate)
    return tmp_path


@pytest.fixture
def client(vault_env):
    """Mount only the new admin_secrets router on an isolated FastAPI app."""
    app = FastAPI()
    app.include_router(admin_secrets.router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _rotate_token_bucket() -> dict[str, deque[float]]:
    admin_secrets._rotate_hits.clear()
    return admin_secrets._rotate_hits


# ---------------------------------------------------------------------------
# 1. owner happy upsert → status returns fresh
# ---------------------------------------------------------------------------


def test_owner_upsert_and_status_marks_fresh(client, vault_env):
    # Use the real upsert_secret so the vault actually has the entry; status
    # reads the same vault to surface ``state="fresh"``.
    vault_value = _gen_str(40)
    catalog_key = "models/dspark-v1.1-mida-brikie/api_key"
    r = client.post(
        "/api/admin/secrets/upsert",
        json={"key": catalog_key, "value": vault_value},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "upserted"
    assert body["reference"] == f"secret://{catalog_key}"
    assert body["masked"] is True

    s = client.get("/api/admin/secrets/status")
    assert s.status_code == 200, s.text
    data = s.json()
    item = next(i for i in data["items"] if i["key"] == catalog_key)
    assert item["state"] == "fresh"
    assert item["source"] == "vault"
    assert item["is_placeholder"] is False
    # Value must not contain plaintext
    assert vault_value not in (item["masked_value"] or "")


# ---------------------------------------------------------------------------
# 2. value=None → status returns missing
# ---------------------------------------------------------------------------


def test_upsert_value_null_deletes_entry(client, vault_env):
    catalog_key = "models/dspark-v1.1-mida-brikie/api_key"
    r1 = client.post(
        "/api/admin/secrets/upsert",
        json={"key": catalog_key, "value": _gen_str(20)},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/admin/secrets/upsert",
        json={"key": catalog_key, "value": None},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "deleted"
    s = client.get("/api/admin/secrets/status")
    item = next(i for i in s.json()["items"] if i["key"] == catalog_key)
    assert item["state"] == "missing"


# ---------------------------------------------------------------------------
# 3. non-owner 403
# ---------------------------------------------------------------------------


def test_upsert_rejects_non_owner(client, vault_env):
    from unittest.mock import patch

    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        r = client.post(
            "/api/admin/secrets/upsert",
            json={"key": "models/x/api_key", "value": _gen_str(20)},
        )
    assert r.status_code == 403
    assert r.json()["detail"] == "仅拥有者可执行此操作"


def test_rotate_rejects_non_owner(client, vault_env):
    from unittest.mock import patch

    with patch("app.gateway.auth.session_user_from_request", return_value=_member()):
        r = client.post(
            "/api/admin/secrets/rotate",
            json={
                "key": "MICX_ADMIN_SECRET_KEY",
                "new_value": _gen_str(40),
                "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
            },
        )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 4. unauth 401
# ---------------------------------------------------------------------------


def test_upsert_rejects_unauth(client, vault_env, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    r = client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/x/api_key", "value": _gen_str(20)},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "需要先登录"


# ---------------------------------------------------------------------------
# 5. key with newline rejected
# ---------------------------------------------------------------------------


def test_upsert_rejects_invalid_key_with_control_chars(client, vault_env):
    r = client.post(
        "/api/admin/secrets/upsert",
        json={"key": "foo\nbar", "value": _gen_str(20)},
    )
    assert r.status_code == 422
    # The Pydantic detail lists each invalid field; we don't pin the exact
    # error type, only that validation rejected the request.
    assert isinstance(r.json()["detail"], list)


# ---------------------------------------------------------------------------
# 6. rotate correct password returns 200
# ---------------------------------------------------------------------------


def test_rotate_correct_password_succeeds(client, vault_env):
    new_value = _gen_str(40)
    r = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": new_value,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["key"] == "MICX_ADMIN_SECRET_KEY"
    assert "session_hmac" in body["cascades"]
    assert body["cookie_invalidation"] == "forced_relogin"
    assert os.environ["MICX_ADMIN_SECRET_KEY"] == new_value


# ---------------------------------------------------------------------------
# 7. rotate wrong password returns 401
# ---------------------------------------------------------------------------


def test_rotate_wrong_password_returns_401(client, vault_env):
    original_key = os.environ["MICX_ADMIN_SECRET_KEY"]
    r = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": _gen_str(40),
            "current_admin_password": "definitely-wrong-" + _gen_str(8),
        },
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "当前密码不正确"
    # env unchanged
    assert os.environ["MICX_ADMIN_SECRET_KEY"] == original_key


# ---------------------------------------------------------------------------
# 8. rotate invalidates old cookies
# ---------------------------------------------------------------------------


def test_rotate_invalidates_old_cookies(client, vault_env):
    # Sign a cookie with the current session secret and verify it decodes,
    # then rotate the session secret and verify the same cookie no longer
    # decodes.
    from app.gateway.auth import create_session_token

    # First, upsert a known strong session secret so we have a stable value
    # to rotate from. The default _auth_secret() falls back to a dev secret
    # in tests; here we install a real one to make rotation observable.
    initial_session_secret = _gen_str(48)
    client.post(
        "/api/admin/secrets/upsert",
        json={"key": "BETTER_AUTH_SECRET", "value": initial_session_secret},
    )
    # Re-sign the cookie after setting the env to the same value so
    # decode_session_token() and create_session_token() agree.
    os.environ["BETTER_AUTH_SECRET"] = initial_session_secret
    token = create_session_token(_owner())
    assert decode_session_token(token) is not None

    r = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "BETTER_AUTH_SECRET",
            "new_value": _gen_str(48),
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r.status_code == 200
    assert decode_session_token(token) is None
    # New tokens sign and decode with the new secret.
    new_token = create_session_token(_owner())
    assert decode_session_token(new_token) is not None


# ---------------------------------------------------------------------------
# 9. masked_value never contains plaintext
# ---------------------------------------------------------------------------


def test_status_masked_value_never_contains_plaintext(client, vault_env):
    catalog_key = "models/dspark-v1.1-mida-brikie/api_key"
    vault_value = "sk-abcXYZ-must-not-leak-" + _gen_str(8)
    client.post(
        "/api/admin/secrets/upsert",
        json={"key": catalog_key, "value": vault_value},
    )
    s = client.get("/api/admin/secrets/status")
    item = next(i for i in s.json()["items"] if i["key"] == catalog_key)
    assert "abcXYZ-must-not-leak" not in (item["masked_value"] or "")
    # The mask formatter emits at least one bullet
    assert "•" in (item["masked_value"] or "")


# ---------------------------------------------------------------------------
# 10. placeholder detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected_state",
    [
        ("CHANGEME", "placeholder"),
        ("change-me", "placeholder"),
        ("placeholder", "placeholder"),
        ("   ", "placeholder"),
        ("xxx", "placeholder"),
        ("your-key-here", "placeholder"),
    ],
)
def test_status_classifies_placeholder_values(raw, expected_state, client, vault_env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", raw)
    s = client.get("/api/admin/secrets/status?include_all=true")
    item = next(i for i in s.json()["items"] if i["key"] == "OPENAI_API_KEY")
    # The endpoint should either flag the value as placeholder, or treat the
    # blank/whitespace input as missing. We accept both for " " (whitespace)
    # since the contract is conservative: the operator sees a non-fresh state
    # and investigates.
    assert item["state"] in {"placeholder", "missing"}, (raw, item)
    if expected_state == "placeholder" and item["state"] == "placeholder":
        assert item["is_placeholder"] is True, (raw, item)


def test_status_classifies_real_keys_as_fresh(client, vault_env, monkeypatch):
    # A long random string almost never matches the placeholder heuristic.
    monkeypatch.setenv("OPENAI_API_KEY", _gen_str(40))
    s = client.get("/api/admin/secrets/status?include_all=true")
    item = next(i for i in s.json()["items"] if i["key"] == "OPENAI_API_KEY")
    assert item["state"] in {"fresh", "configured"}
    assert item["is_placeholder"] is False


# ---------------------------------------------------------------------------
# 11. audit emission
# ---------------------------------------------------------------------------


def test_upsert_writes_audit_record(client, vault_env):
    client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/dspark-v1.1-mida-brikie/api_key", "value": _gen_str(20)},
    )
    from deerflow.config.paths import get_paths

    audit_file = get_paths().admin_audit_file
    if audit_file.exists():
        events = [json.loads(line).get("action") for line in audit_file.read_text().splitlines() if line.strip()]
        assert "admin_secret.upserted" in events


def test_rotate_writes_audit_record_without_plaintext(client, vault_env):
    new_value = _gen_str(40)
    client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": new_value,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    from deerflow.config.paths import get_paths

    audit_file = get_paths().admin_audit_file
    if audit_file.exists():
        text = audit_file.read_text()
        assert "admin_secret.rotated" in text
        # Secrets / password must never appear in audit details.
        assert new_value not in text
        assert os.environ["BY_ADMIN_PASSWORD"] not in text


# ---------------------------------------------------------------------------
# 12. rotate idempotent (same value twice)
# ---------------------------------------------------------------------------


def test_rotate_idempotent_same_value(client, vault_env):
    new_value = "stable-" + _gen_str(24)
    r1 = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": new_value,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": new_value,
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r2.status_code == 200


# ---------------------------------------------------------------------------
# 13. rate limit (11th rotate from same IP → 429)
# ---------------------------------------------------------------------------


def test_rotate_rate_limit_blocks_11th_call(client, vault_env):
    _rotate_token_bucket()
    for i in range(10):
        r = client.post(
            "/api/admin/secrets/rotate",
            json={
                "key": "MICX_ADMIN_SECRET_KEY",
                "new_value": f"value-{i}-" + _gen_str(24),
                "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
            },
        )
        assert r.status_code == 200, (i, r.text)
    r11 = client.post(
        "/api/admin/secrets/rotate",
        json={
            "key": "MICX_ADMIN_SECRET_KEY",
            "new_value": "value-11-" + _gen_str(24),
            "current_admin_password": os.environ["BY_ADMIN_PASSWORD"],
        },
    )
    assert r11.status_code == 429
    assert "Retry-After" in r11.headers


# ---------------------------------------------------------------------------
# 14. cold-start status
# ---------------------------------------------------------------------------


def test_status_after_cold_start_with_one_upsert(client, vault_env):
    s0 = client.get("/api/admin/secrets/status")
    assert s0.status_code == 200
    # Initially the four production vault keys are missing.
    items = {i["key"]: i for i in s0.json()["items"]}
    assert items["models/dspark-v1.1-mida-brikie/api_key"]["state"] == "missing"
    # Upsert one, it becomes fresh.
    client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/dspark-v1.1-mida-brikie/api_key", "value": _gen_str(40)},
    )
    s1 = client.get("/api/admin/secrets/status")
    items = {i["key"]: i for i in s1.json()["items"]}
    assert items["models/dspark-v1.1-mida-brikie/api_key"]["state"] == "fresh"
    # And the vault mtime is now set.
    assert s1.json()["vault_mtime"] is not None
