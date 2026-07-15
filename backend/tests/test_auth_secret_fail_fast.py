"""V01 — fail-fast + dev-default rejection tests for `app.gateway.auth._auth_secret`.

These tests assert the behavior documented in the pentest remediation:
- ``_auth_secret()`` raises ``RuntimeError`` when ``BETTER_AUTH_SECRET`` is unset
  and the dev escape hatch is not opted in.
- The well-known development default string is also rejected unless the
  operator explicitly opts in via ``BY_ALLOW_DEV_AUTH_SECRET=1``.
- The escape hatch never fires when ``ENV=production``.
- When opted in, the development default is returned (and only the dev default).

We deliberately exercise the helper directly rather than going through HTTP,
because the failure mode is at module-import time and we want a sharp signal
when the policy regresses.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

AUTH_MODULE = "app.gateway.auth"


def _reload_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload the auth module so module-level env reads re-evaluate.

    Important: this helper does NOT touch env vars itself. Callers must set
    every relevant env var (or call ``monkeypatch.delenv``) before invoking
    this so the reload happens with the desired final state.
    """
    if AUTH_MODULE in importlib.sys.modules:
        importlib.reload(importlib.import_module(AUTH_MODULE))
    else:
        importlib.import_module(AUTH_MODULE)


def test_auth_secret_raises_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BETTER_AUTH_SECRET", raising=False)
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)

    with pytest.raises(RuntimeError, match="BETTER_AUTH_SECRET"):
        auth._auth_secret()  # noqa: SLF001 — intentional black-box test


def test_auth_secret_allows_dev_default_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BETTER_AUTH_SECRET", raising=False)
    monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", "1")
    monkeypatch.delenv("ENV", raising=False)
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)

    assert auth._auth_secret() == auth._DEV_AUTH_SECRET  # noqa: SLF001


def test_auth_secret_rejects_well_known_dev_default_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", "by-local-dev-secret")
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)

    with pytest.raises(RuntimeError, match="well-known development default"):
        auth._auth_secret()  # noqa: SLF001


def test_auth_secret_never_allows_dev_default_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even with the explicit opt-in flag, production must refuse the dev default."""
    monkeypatch.delenv("BETTER_AUTH_SECRET", raising=False)
    monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", "1")
    monkeypatch.setenv("ENV", "production")
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)

    with pytest.raises(RuntimeError, match="BETTER_AUTH_SECRET"):
        auth._auth_secret()  # noqa: SLF001


def test_auth_secret_returns_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", "a-strong-random-secret-of-32-chars-min")
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)

    assert auth._auth_secret() == "a-strong-random-secret-of-32-chars-min"  # noqa: SLF001


def test_is_dev_secret_allowed_truth_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("BY_ALLOW_DEV_AUTH_SECRET", raising=False)
    _reload_auth(monkeypatch)
    auth = importlib.import_module(AUTH_MODULE)
    assert auth._is_dev_secret_allowed() is False  # noqa: SLF001

    monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", "1")
    assert auth._is_dev_secret_allowed() is True  # noqa: SLF001

    monkeypatch.setenv("ENV", "production")
    assert auth._is_dev_secret_allowed() is False  # noqa: SLF001

    # Variants of truthy values
    monkeypatch.setenv("ENV", "development")
    for value in ("true", "True", "yes", "YES", "1"):
        monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", value)
        assert auth._is_dev_secret_allowed() is True, value  # noqa: SLF001

    for value in ("0", "no", "false", "off", ""):
        monkeypatch.setenv("BY_ALLOW_DEV_AUTH_SECRET", value)
        assert auth._is_dev_secret_allowed() is False, value  # noqa: SLF001


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts from a clean slate for the relevant env vars."""
    for var in ("BETTER_AUTH_SECRET", "BY_ALLOW_DEV_AUTH_SECRET", "ENV"):
        monkeypatch.delenv(var, raising=False)
    yield
    # Reload one more time at teardown so subsequent tests in the same process
    # do not inherit a module that captured test env values.
    _reload_auth(monkeypatch)


# Avoid linting warnings about unused imports
_ = Path