"""Helper-layer unit tests for v1.6.2 admin secrets endpoints."""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

import pytest

from deerflow.admin.secrets import (
    KNOWN_SECRET_KEYS,
    KNOWN_VAULT_KEYS,
    SECRET_REF_PREFIX,
    _vault_path,
    delete_secret,
    get_vault_mtime,
    is_placeholder_value,
    rotate_env_secret,
    upsert_secret,
)
from deerflow.config.paths import Paths


def _patch_paths(monkeypatch, tmp_path):
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr(
        "deerflow.admin.secrets.get_paths",
        lambda: paths,
    )
    return paths


# ---------------------------------------------------------------------------
# KNOWN_SECRET_KEYS / KNOWN_VAULT_KEYS
# ---------------------------------------------------------------------------


def test_known_secret_keys_covers_required_auth_and_providers():
    # PRD requires BETTER_AUTH_SECRET + MICX_ADMIN_SECRET_KEY; the catalog must
    # include every key the v1.6.x `config.yaml` references.
    assert "BETTER_AUTH_SECRET" in KNOWN_SECRET_KEYS
    assert "MICX_ADMIN_SECRET_KEY" in KNOWN_SECRET_KEYS
    assert "OPENAI_API_KEY" in KNOWN_SECRET_KEYS
    assert "ANTHROPIC_API_KEY" in KNOWN_SECRET_KEYS
    # LLM vendors added in v1.6.2 vendor catalog
    for vendor_key in ("DEEPSEEK_API_KEY", "GOOGLE_API_KEY", "ALIYUN_API_KEY",
                        "VOLCENGINE_API_KEY", "MOONSHOT_API_KEY"):
        assert vendor_key in KNOWN_SECRET_KEYS, f"missing {vendor_key}"


def test_known_vault_keys_lists_four_production_models():
    # PRD requires one vault key per production model currently in models.override.yaml
    expected = {
        "models/dspark-v1.1-mida-brikie/api_key",
        "models/mixh-coder/api_key",
        "models/Qwen3-5-35B-A3B-Claude-4-6-Opus-Reasoning/api_key",
        "models/MicX Service/api_key",
    }
    assert expected.issubset(set(KNOWN_VAULT_KEYS))


# ---------------------------------------------------------------------------
# is_placeholder_value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("\t\n", True),
        ("CHANGEME", True),
        ("change-me", True),
        ("placeholder", True),
        ("sk-local-placeholder", True),
        ("xxxx", True),
        ("TODO", True),
        ("your-key-here", True),
        ("foo", True),
        ("sk-real-LqWJ9b-Xv_8q3KpM7nZ2hE4cR6sT1yU0iO", False),
        ("AIzaSyDa-fake-12char-key-zzzzzzzzzz", False),
    ],
)
def test_is_placeholder_value_matrix(raw, expected):
    assert is_placeholder_value(raw) is expected, (raw, expected)


# ---------------------------------------------------------------------------
# delete_secret
# ---------------------------------------------------------------------------


def test_delete_secret_removes_existing(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    upsert_secret("foo/api_key", "sk-abc")
    assert delete_secret("foo/api_key") is True
    # Re-upsert returns a fresh reference; nothing left of the old one.
    upsert_secret("foo/api_key", "sk-xyz")
    raw = _vault_path().read_bytes()
    from cryptography.fernet import Fernet
    from deerflow.admin.secrets import _vault_cipher
    decrypted = json.loads(_vault_cipher().decrypt(raw).decode("utf-8"))
    assert decrypted == {"foo/api_key": "sk-xyz"}


def test_delete_secret_returns_false_when_missing(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    assert delete_secret("does-not-exist") is False


def test_delete_secret_rejects_empty_key():
    with pytest.raises(ValueError, match="cannot be empty"):
        delete_secret("")
    with pytest.raises(ValueError, match="cannot be empty"):
        delete_secret("   ")


# ---------------------------------------------------------------------------
# get_vault_mtime
# ---------------------------------------------------------------------------


def test_get_vault_mtime_returns_none_when_missing(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    assert get_vault_mtime() is None


def test_get_vault_mtime_advances_after_write(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    assert get_vault_mtime() is None
    upsert_secret("foo/api_key", "sk-abc")
    before = get_vault_mtime()
    assert before is not None
    time.sleep(1.05)
    upsert_secret("foo/api_key", "sk-xyz")
    after = get_vault_mtime()
    assert after > before


# ---------------------------------------------------------------------------
# rotate_env_secret
# ---------------------------------------------------------------------------


@pytest.fixture
def restore_env(monkeypatch):
    """Snapshot relevant env vars and restore them after the test."""
    snapshot = {k: os.environ.get(k) for k in (*KNOWN_SECRET_KEYS, "BY_ADMIN_PASSWORD")}
    yield
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_rotate_env_secret_sets_os_environ(monkeypatch, restore_env):
    rotate_env_secret("TAVILY_API_KEY", "tvly-new-value")
    assert os.environ["TAVILY_API_KEY"] == "tvly-new-value"


def test_rotate_env_secret_cascades_for_session_hmac(monkeypatch, restore_env):
    cascades = rotate_env_secret("BETTER_AUTH_SECRET", "fresh-better-auth-secret")
    assert "session_hmac" in cascades
    assert "vault_cipher" in cascades


def test_rotate_env_secret_cascades_for_vault_cipher(monkeypatch, restore_env):
    cascades = rotate_env_secret("MICX_ADMIN_SECRET_KEY", "fresh-vault-cipher")
    assert "vault_cipher" in cascades
    assert "session_hmac" in cascades


def test_rotate_env_secret_no_cascade_for_unrelated_key(monkeypatch, restore_env):
    cascades = rotate_env_secret("TAVILY_API_KEY", "x")
    assert cascades == []


def test_rotate_env_secret_rejects_invalid_arguments(monkeypatch, restore_env):
    with pytest.raises(ValueError):
        rotate_env_secret("", "value")
    with pytest.raises(ValueError):
        rotate_env_secret(None, "value")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        rotate_env_secret("X", 123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# roundtrip with vault
# ---------------------------------------------------------------------------


def test_secret_ref_prefix_constant():
    assert SECRET_REF_PREFIX == "secret://"


def test_upsert_secret_then_resolve_secret_ref_roundtrip(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    ref = upsert_secret("models/dspark/api_key", "sk-real-XYZ")
    assert ref == "secret://models/dspark/api_key"
    from deerflow.admin.secrets import resolve_secret_ref
    assert resolve_secret_ref(ref) == "sk-real-XYZ"
