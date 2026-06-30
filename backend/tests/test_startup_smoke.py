"""Unit-level smoke for the v1.5.7 connector startup integration.

This complements `test_app_lifespan.py`: where that test verifies the
helpers are wired correctly, this one verifies the *full path* from
`os.environ["MICX_CONNECTORS"]` through YAML parse to registry entries.

We don't boot the FastAPI app here (that's expensive and the harness's
AppConfig Pydantic schema is too strict for a tmp config). Instead we
exercise the same code paths the lifespan runs.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.gateway.connectors.integrations.builtin import register_builtin_connectors
from app.gateway.connectors.registry import ConnectorRegistry, reset_registry
from app.gateway.connectors.persistence.sqlite_dlq import (
    SqliteDLQStore,
    flush_to_sqlite,
)
from app.gateway.connectors.dlq import InMemoryDLQStore


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


def test_smoke_micx_connectors_env_path_to_registry():
    """The full env → YAML → register_builtin_connectors path, as
    the lifespan would run it."""
    import yaml

    os.environ["MICX_CONNECTORS"] = """
    feishu:
      app_id: cli_smoke
      app_secret: sec_smoke
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
        names = set(reg.list_names())
        assert {"feishu", "email"}.issubset(names)
    finally:
        del os.environ["MICX_CONNECTORS"]


def test_smoke_dlq_round_trip_via_sqlite(tmp_path: Path):
    """Simulate the shutdown-flush path: in-memory store + sqlite."""
    mem = InMemoryDLQStore()
    mem.push({
        "connector": "feishu",
        "error": "smtp down",
        "attempts": 3,
        "message": {"text": "queue overflow", "target": {"chat_id": "c1"}},
    })
    sq = SqliteDLQStore(tmp_path / "dlq.db")
    try:
        n = flush_to_sqlite(mem, sq)
        assert n == 1
        # The in-memory store is now empty (production flush clears it).
        assert mem.list_all() == []
        # The sqlite store holds the entry.
        items = sq.list_all()
        assert items[0]["error"] == "smtp down"
        assert items[0]["message"]["text"] == "queue overflow"
    finally:
        sq.close()


def test_smoke_dlq_visible_in_admin_after_restart(tmp_path: Path):
    """The crucial user-facing property: after gateway restart, admin
    can still see historical DLQ entries.
    """
    mem = InMemoryDLQStore()
    mem.push({
        "connector": "feishu",
        "error": "rate limited",
        "attempts": 2,
        "message": {"text": "x", "target": {}},
    })
    sq_path = tmp_path / "dlq.db"
    sq1 = SqliteDLQStore(sq_path)
    flush_to_sqlite(mem, sq1)
    sq1.close()

    # Simulate restart: new in-memory store, fresh sqlite connection.
    fresh_mem = InMemoryDLQStore()
    fresh_sq = SqliteDLQStore(sq_path)
    try:
        historical = fresh_sq.list_all()
        assert any(i["error"] == "rate limited" for i in historical)
        assert fresh_mem.list_all() == []  # in-memory starts empty
    finally:
        fresh_sq.close()
