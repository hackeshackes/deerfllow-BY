"""Tests for the multi-region replication config + wiring (v1.7 M4).

Two layers:
1. Config: ``load_replication_config`` parses the ``SECRETS_REPLICATION_*``
   env surface into a frozen ``ReplicationConfig``; absent config → disabled
   (no throw).
2. Wiring: ``pull_replica_to_cache`` / ``push_local_to_replica`` bridge the
   vault read/write path to the manager via a fake manager + fake vault I/O.
"""

from __future__ import annotations

import json

import pytest

from deerflow.admin.replication_config import load_replication_config
from deerflow.admin.replication_wiring import (
    build_rep_manager,
    pull_replica_to_cache,
    push_local_to_replica,
)


def _env(**overrides: str) -> dict[str, str]:
    base = {
        "SECRETS_REPLICATION_ENABLED": "true",
        "SECRETS_REPLICATION_REGION": "us-east-1",
        "SECRETS_REPLICATION_REMOTE": "vaults/${REGION}/secrets.json",
        "SECRETS_REPLICATION_ACCESS_KEY": "AKIATEST",
        "SECRETS_REPLICATION_SECRET_KEY": "testsecret",
        "SECRETS_REPLICATION_ENDPOINT": "https://s3.us-east-1.amazonaws.com",
        "SECRETS_REPLICATION_BUCKET": "secrets-bucket",
        "SECRETS_REPLICATION_KMS_KEY_ID": "arn:aws:kms:us-east-1:123:key/abc",
    }
    base.update(overrides)
    return base


# ---- config -------------------------------------------------------------


def test_disabled_no_env_returns_default_disabled():
    cfg = load_replication_config({})
    assert cfg.enabled is False
    assert cfg.region is None


def test_enabled_env_parses_fields():
    cfg = load_replication_config(_env())
    assert cfg.enabled is True
    assert cfg.region == "us-east-1"
    assert cfg.remote == "vaults/us-east-1/secrets.json"  # ${REGION} expanded
    assert cfg.endpoint == "https://s3.us-east-1.amazonaws.com"
    assert cfg.access_key == "AKIATEST"
    assert cfg.bucket == "secrets-bucket"


def test_disabled_when_explicit_false():
    cfg = load_replication_config(_env(SECRETS_REPLICATION_ENABLED="false"))
    assert cfg.enabled is False


def test_partial_env_without_enabled_flag_stays_disabled():
    """Presence of keys but no ENABLED=true must not silently enable."""
    cfg = load_replication_config(
        {
            "SECRETS_REPLICATION_REGION": "eu-west-1",
            "SECRETS_REPLICATION_ACCESS_KEY": "AKIATEST",
        }
    )
    assert cfg.enabled is False


# --- wiring -------------------------------------------------------------


class _FakeManager:
    def __init__(self) -> None:
        self.remote_blob: bytes | None = None
        self.pulled: list[str] = []
        self.pushed: list[bytes] = []

    async def pull(self, remote: str) -> bytes | None:
        self.pulled.append(remote)
        return self.remote_blob

    async def push(self, remote: str, plaintext: bytes, *, expect_matches=None):  # noqa: ANN001
        self.pushed.append(plaintext)


def _fake_vault(monkeypatch, initial: dict[str, str] | None = None) -> dict[str, str]:
    """Point the wiring module's vault read/write at an in-memory dict."""
    store: dict[str, str] = dict(initial or {})

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring._read_secret_map",
        lambda: dict(store),
    )

    def _write(values: dict[str, str]) -> None:
        store.clear()
        store.update(values)

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring._write_secret_map",
        _write,
    )
    return store


@pytest.mark.asyncio
async def test_pull_writes_remote_blob_to_local_vault(monkeypatch):
    cfg = load_replication_config(_env())
    manager = _FakeManager()
    manager.remote_blob = json.dumps({"models/foo/api_key": "sekrit"}).encode()

    local_store = _fake_vault(monkeypatch, initial={"models/foo/api_key": "old"})

    await pull_replica_to_cache(cfg, manager)

    assert manager.pulled == [cfg.remote]
    assert local_store["models/foo/api_key"] == "sekrit"


@pytest.mark.asyncio
async def test_pull_no_remote_blob_is_noop(monkeypatch):
    cfg = _env()
    cfg_obj = load_replication_config(cfg)
    manager = _FakeManager()  # remote_blob stays None
    local_store = _fake_vault(monkeypatch, initial={"k": "v"})

    await pull_replica_to_cache(cfg_obj, manager)

    assert manager.pulled == [cfg["SECRETS_REPLICATION_REMOTE"].replace("${REGION}", "us-east-1")]
    assert local_store == {"k": "v"}  # untouched


@pytest.mark.asyncio
async def test_push_uploads_plaintext_vault_to_remote(monkeypatch):
    cfg = load_replication_config(_env())
    manager = _FakeManager()
    _fake_vault(monkeypatch, initial={"k": "v", "k2": "v2"})

    await push_local_to_replica(cfg, manager, actor_id="u1")

    assert len(manager.pushed) == 1
    # The pushed plaintext is the vault's JSON dict serialized.
    parsed = json.loads(manager.pushed[0])
    assert parsed == {"k": "v", "k2": "v2"}


def test_build_rep_manager_returns_none_when_disabled():
    cfg = load_replication_config({})  # disabled
    assert build_rep_manager(cfg) is None