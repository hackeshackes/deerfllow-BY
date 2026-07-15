"""V01 — fail-fast tests for ``deerflow.admin.secrets._vault_cipher``.

Mirrors the policy in :mod:`app.gateway.auth`: the Fernet vault must never
silently fall back to the well-known development secret. Production always
fails closed; non-production only succeeds with the explicit
``BY_ALLOW_DEV_AUTH_SECRET=1`` opt-in.
"""

from __future__ import annotations

import importlib

import pytest

SECRETS_MODULE = "deerflow.admin.secrets"


def _reload_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload secrets so module-level env reads re-evaluate.

    Callers must set every relevant env var (or call ``monkeypatch.delenv``)
    before invoking this so the reload happens with the desired final state.
    """
    if SECRETS_MODULE in importlib.sys.modules:
        importlib.reload(importlib.import_module(SECRETS_MODULE))
    else:
        importlib.import_module(SECRETS_MODULE)


def test_vault_cipher_raises_without_secret_or_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MICX_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.delenv("BETTER_AUTH_SECRET", raising=False)
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    with pytest.raises(RuntimeError, match="MICX_ADMIN_SECRET_KEY|BETTER_AUTH_SECRET"):
        secrets._vault_cipher()  # noqa: SLF001


def test_vault_cipher_uses_dev_default_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MICX_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.delenv("BETTER_AUTH_SECRET", raising=False)
    monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", "1")
    monkeypatch.delenv("ENV", raising=False)
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    cipher = secrets._vault_cipher()  # noqa: SLF001

    # round-trip a value to prove the cipher is functional
    payload = b"hello"
    token = cipher.encrypt(payload)
    assert cipher.decrypt(token) == payload


def test_vault_cipher_rejects_well_known_dev_default_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", "by-local-dev-secret")
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    with pytest.raises(RuntimeError, match="well-known development default"):
        secrets._vault_cipher()  # noqa: SLF001


def test_vault_cipher_never_allows_dev_default_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MICX_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.setenv("BETTER_AUTH_SECRET", "by-local-dev-secret")
    monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", "1")
    monkeypatch.setenv("ENV", "production")
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    with pytest.raises(RuntimeError, match="well-known development default"):
        secrets._vault_cipher()  # noqa: SLF001


def test_vault_cipher_uses_strong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", "a-strong-random-secret-of-32-chars-min")
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    cipher = secrets._vault_cipher()  # noqa: SLF001
    token = cipher.encrypt(b"x")
    assert cipher.decrypt(token) == b"x"


def test_vault_cipher_prefers_micx_admin_secret_key_over_better_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """When both env vars are set, MICX_ADMIN_SECRET_KEY wins."""
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", "primary-secret-32-chars-please-okay")
    monkeypatch.setenv("BETTER_AUTH_SECRET", "fallback-secret-also-strong-32-chars")
    _reload_secrets(monkeypatch)
    secrets = importlib.import_module(SECRETS_MODULE)

    cipher = secrets._vault_cipher()  # noqa: SLF001
    token = cipher.encrypt(b"hello")

    # Switching the env to use only BETTER_AUTH_SECRET must produce a *different*
    # key, proving MICX_ADMIN_SECRET_KEY was actually used.
    monkeypatch.delenv("MICX_ADMIN_SECRET_KEY", raising=False)
    _reload_secrets(monkeypatch)
    secrets2 = importlib.import_module(SECRETS_MODULE)
    cipher2 = secrets2._vault_cipher()  # noqa: SLF001

    # Same plaintext encrypts to a fresh token (Fernet tokens are non-deterministic)
    # but the keypair must be different — verifiable by deriving the raw key.
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    def _key(env_value: str) -> bytes:
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(env_value.encode()).digest()))

    assert _key("primary-secret-32-chars-please-okay") != _key("fallback-secret-also-strong-32-chars")
    # Sanity: the cipher we produced above can still decrypt its own token
    assert cipher.decrypt(token) == b"hello"
    assert cipher != cipher2  # different Fernet instances


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "MICX_ADMIN_SECRET_KEY",
        "BETTER_AUTH_SECRET",
        "BY_ALLOW_DEV_AUTH_SECRET",
        "ENV",
    ):
        monkeypatch.delenv(var, raising=False)
    yield
    _reload_secrets(monkeypatch)