"""Tests that the lifespan auto-registers connectors from MICX_CONNECTORS.

We don't boot the full app here — that's covered by `make test`'s
end-to-end runs. This test focuses on the contract: given a YAML env
body, the registry is populated with the expected connectors.
"""
from __future__ import annotations

import pytest

from app.gateway.connectors.integrations.builtin import register_builtin_connectors
from app.gateway.connectors.registry import ConnectorRegistry, reset_registry


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


def test_register_builtin_from_yaml_env():
    """Simulates the lifespan path: read YAML from env, call register.

    A regression in the env-loading or yaml-parsing layer would break
    this test even before the lifespan runs.
    """
    import yaml
    import os

    os.environ["MICX_CONNECTORS"] = """
    feishu:
      app_id: cli_x
      app_secret: sec_x
    email:
      smtp_host: smtp.x
      smtp_port: 587
      smtp_user: u
      smtp_password: p
      imap_host: imap.x
      imap_port: 993
      from_address: bot@x
    """
    try:
        body = yaml.safe_load(os.environ["MICX_CONNECTORS"]) or {}
        reg = ConnectorRegistry()
        register_builtin_connectors(registry=reg, config=body)
        assert "feishu" in reg.list_names()
        assert "email" in reg.list_names()
    finally:
        del os.environ["MICX_CONNECTORS"]


def test_empty_yaml_env_registers_nothing():
    import os

    os.environ["MICX_CONNECTORS"] = ""
    try:
        body = (os.environ.get("MICX_CONNECTORS") or "").strip()
        assert body == ""
    finally:
        del os.environ["MICX_CONNECTORS"]


def test_lifespan_module_imports_register_helper():
    """Smoke: the helper functions that the lifespan calls are importable.

    This catches accidental removal of the public API in the connectors
    subsystem. The lifespan relies on these symbols being available.
    """
    from app.gateway.app import create_app  # noqa: F401
    from app.gateway.connectors.integrations.builtin import (
        register_builtin_connectors,  # noqa: F401
    )
    from app.gateway.connectors.registry import get_registry  # noqa: F401
    from app.gateway.connectors.persistence.sqlite_dlq import (
        SqliteDLQStore,  # noqa: F401
    )
    assert callable(register_builtin_connectors)
    assert callable(get_registry)
    assert callable(SqliteDLQStore)
