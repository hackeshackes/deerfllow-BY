"""Tests that admin secrets writes trigger a best-effort replication push (v1.7 M4).

The write endpoints (upsert / delete / rotate) call ``_replicate_after_write``
after persisting the vault. That helper imports the wiring lazily, so we patch
the harness-level ``deerflow.admin.replication_wiring`` symbols directly.
"""

from __future__ import annotations

import pytest

from app.gateway.routers.admin_secrets import _replicate_after_write


@pytest.mark.asyncio
async def test_replicate_after_write_calls_push_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "deerflow.admin.replication_config.load_replication_config",
        lambda: "cfg",
    )
    pushed: list[tuple] = []

    async def _fake_push(config, *, actor_id):  # noqa: ANN001
        pushed.append((config, actor_id))

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring.push_local_to_replica",
        _fake_push,
    )

    await _replicate_after_write("u1")

    assert pushed == [("cfg", "u1")]


@pytest.mark.asyncio
async def test_replicate_after_write_tolerates_push_failure(monkeypatch):
    """A push failure must never propagate — the write already succeeded."""

    async def _boom(config, *, actor_id):  # noqa: ANN001
        raise RuntimeError("S3 unreachable")

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring.push_local_to_replica",
        _boom,
    )

    # Should not raise.
    await _replicate_after_write("u1")


@pytest.mark.asyncio
async def test_replicate_after_write_noop_when_push_returns(monkeypatch):
    """Disabled config → push is a no-op; nothing raised and nothing asserted."""

    async def _noop(config, *, actor_id):  # noqa: ANN001
        assert config is not None

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring.push_local_to_replica",
        _noop,
    )

    await _replicate_after_write("u1")