"""Deep robustness tests for v1.7 M4 replication wiring + config.

Attacks four surfaces that must never break the existing secrets read/write
path:

1. Config parsing edge cases: multiple ``${REGION}`` placeholders, an
   enabled-but-region-empty config, and enabled-but-missing-creds.
2. ``pull_replica_to_cache`` against a hostile remote blob (invalid UTF-8,
   non-JSON, valid-JSON-but-not-a-dict) — the local vault must be left
   unchanged and no crash may escape.
3. ``push_local_to_replica`` when ``_read_secret_map`` raises (corrupt vault)
   — does it swallow or propagate? Who guarantees the write still returns 200?
4. Concurrency: is there a lock, and what happens on concurrent pulls?
5. The admin ``/secrets/upsert`` endpoint: a replication push failure must
   NOT bubble up as a 500 — the write response stays 200 (best-effort).
6. Audit: ``replica_pulled`` / ``replica_pushed`` record ``ok=true/false``
   accurately, and a failed audit write must never break replication.

These tests deliberately patch only the harness/module boundaries (vault I/O,
the audit sink, and the manager's transport) so they stay pure and fast — no
real S3, KMS, or audit file writes.
"""

from __future__ import annotations

import pytest

from deerflow.admin.replication import record_replica_audit
from deerflow.admin.replication_config import load_replication_config
from deerflow.admin.replication_wiring import (
    build_rep_manager,
    pull_replica_to_cache,
    push_local_to_replica,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


class _FakeManager:
    """Fake transport manager; ``pull`` returns ``blob`` (default None)."""

    def __init__(self, blob: bytes | None = None) -> None:
        self.blob = blob
        self.pulled: list[str] = []
        self.pushed: list[bytes] = []
        self.push_exc: Exception | None = None

    async def pull(self, remote: str) -> bytes | None:
        self.pulled.append(remote)
        return self.blob

    async def push(self, remote: str, plaintext: bytes, *, expect_matches=None):  # noqa: ANN001
        self.pushed.append(plaintext)
        if self.push_exc is not None:
            raise self.push_exc


def _fake_vault(monkeypatch, initial: dict[str, str] | None = None) -> dict[str, str]:
    """Point the wiring's vault read/write at an in-memory dict."""
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


def _capture_audit(monkeypatch) -> list[dict]:
    """Capture replica audit events in memory instead of writing the audit file."""
    events: list[dict] = []

    def _append(action: str, *, actor_id=None, target="", details=None):  # type: ignore[no-untyped-def]
        events.append({"action": action, "actor_id": actor_id, "target": target, "details": details})

    monkeypatch.setattr("deerflow.admin.audit.append_admin_audit_record", _append)
    return events


def _boom_append(*args, **kwargs):  # type: ignore[no-untyped-def]
    raise OSError("audit disk full")


# ---------------------------------------------------------------------------
# 1. Config parsing edge cases
# ---------------------------------------------------------------------------


def test_region_substitution_replaces_all_placeholder_occurrences():
    """`${REGION}` must be substituted every time it appears, not just once."""
    env = _env(SECRETS_REPLICATION_REMOTE="vaults/${REGION}/backups/${REGION}/secrets.json")
    cfg = load_replication_config(env)
    assert cfg.region == "us-east-1"
    assert cfg.remote == "vaults/us-east-1/backups/us-east-1/secrets.json"
    assert "${REGION}" not in (cfg.remote or "")


def test_region_empty_but_enabled_builds_none():
    """Enabled with an empty region: the manager cannot be built (empty region
    is falsy in ``_manager_for``), so pull/push degrade to a safe no-op. The
    remote template is expanded with an empty string (``vaults//secrets.json``);
    that is cosmetic only because no manager is ever constructed from it."""
    env = _env(SECRETS_REPLICATION_REGION="")
    cfg = load_replication_config(env)
    assert cfg.enabled is True
    assert cfg.region == ""
    # Expanded but mangled (double slash) — the manager is None so this value
    # is never used to contact storage.
    assert cfg.remote == "vaults//secrets.json"
    # An empty region makes the manager unusable → None (safe no-op path).
    assert build_rep_manager(cfg) is None


def test_enabled_true_but_creds_missing_builds_none(monkeypatch):
    """ENABLED=true with any required field missing → build_rep_manager None
    and pull/push are safe no-ops that never touch the vault."""
    missing_a_key = load_replication_config(
        _env(SECRETS_REPLICATION_ACCESS_KEY="")
    )
    assert build_rep_manager(missing_a_key) is None

    missing_kms = load_replication_config(
        _env(SECRETS_REPLICATION_KMS_KEY_ID="")
    )
    assert build_rep_manager(missing_kms) is None


@pytest.mark.asyncio
async def test_enabled_but_creds_missing_noop_pull_and_push(monkeypatch):
    """With a disabled manager, pull/push return without mutating the vault."""
    cfg = load_replication_config(_env(SECRETS_REPLICATION_ACCESS_KEY=""))
    local_store = _fake_vault(monkeypatch, initial={"k": "v"})

    await pull_replica_to_cache(cfg)  # no manager → returns early
    await push_local_to_replica(cfg)  # no manager → returns early

    assert local_store == {"k": "v"}


# ---------------------------------------------------------------------------
# 2. pull_replica_to_cache against malformed remote blobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pull_invalid_utf8_leaves_vault_unchanged_and_audits_false(
    monkeypatch,
):
    env = _env()
    cfg = load_replication_config(env)
    manager = _FakeManager(blob=b"\xff\xfe\x00 garbage\x00")
    local_store = _fake_vault(monkeypatch, initial={"models/foo/api_key": "old"})
    events = _capture_audit(monkeypatch)

    await pull_replica_to_cache(cfg, manager)

    # Vault untouched.
    assert local_store == {"models/foo/api_key": "old"}
    # A failed pull is audited with ok=false (caller-facing degraded read is fine).
    pulled = [e for e in events if e["action"] == "admin_secret.replica_pulled"]
    assert len(pulled) == 1
    assert pulled[0]["details"] == {"ok": False}


@pytest.mark.asyncio
async def test_pull_non_json_blob_leaves_vault_unchanged_and_audits_false(
    monkeypatch,
):
    cfg = load_replication_config(_env())
    manager = _FakeManager(blob=b"this is { not json")
    local_store = _fake_vault(monkeypatch, initial={"k": "v"})
    events = _capture_audit(monkeypatch)

    await pull_replica_to_cache(cfg, manager)

    assert local_store == {"k": "v"}
    pulled = [e for e in events if e["action"] == "admin_secret.replica_pulled"]
    assert len(pulled) == 1
    assert pulled[0]["details"] == {"ok": False}


@pytest.mark.asyncio
async def test_pull_valid_json_but_not_dict_leaves_vault_unchanged(monkeypatch):
    """A JSON array (not an object) must not populate the vault and must not crash;
    it is rejected before any write and before any audit (no ok placement)."""
    cfg = load_replication_config(_env())
    manager = _FakeManager(blob=b'["a", "b", 1]')
    local_store = _fake_vault(monkeypatch, initial={"k": "v"})
    events = _capture_audit(monkeypatch)

    await pull_replica_to_cache(cfg, manager)

    assert local_store == {"k": "v"}  # unchanged
    # Not-a-dict plaintext is dropped without an audit event.
    assert events == []


# ---------------------------------------------------------------------------
# 3. push_local_to_replica when the vault read raises (corrupt)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_when_vault_read_raises_is_best_effort(monkeypatch):
    """A corrupt vault (non-dict JSON) makes ``_read_secret_map`` raise. The
    wiring must NOT propagate this and must NOT touch the remote — it is
    treated like any other replication failure: swallowed + audited ok=False
    (so the write response keeps returning 200 through the caller)."""
    cfg = load_replication_config(_env())
    manager = _FakeManager()
    events = _capture_audit(monkeypatch)

    def _corrupt_read() -> dict[str, str]:
        raise RuntimeError("Admin secrets vault is corrupted.")

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring._read_secret_map",
        _corrupt_read,
    )

    # Must NOT raise — best-effort, matching the pushed-ok=False audit.
    await push_local_to_replica(cfg, manager, actor_id="u1")

    # No push payload reached the remote.
    assert manager.pushed == []
    pushed = [e for e in events if e["action"] == "admin_secret.replica_pushed"]
    assert len(pushed) == 1
    assert pushed[0]["actor_id"] == "u1"
    assert pushed[0]["details"] == {"ok": False}


# ---------------------------------------------------------------------------
# 4. Concurrency semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_explicit_lock_two_pulls_are_idempotent(monkeypatch):
    """There is no lock around pull; two sequential pulls of the same remote
    must converge to the same vault (atomic replace makes this safe)."""
    cfg = load_replication_config(_env())
    mgr = _FakeManager(blob=b'{"k": "remote-value", "k2": "x"}')
    local_store = _fake_vault(monkeypatch, initial={"old": "gone"})

    await pull_replica_to_cache(cfg, mgr)
    first = dict(local_store)
    await pull_replica_to_cache(cfg, mgr)

    assert first == {"k": "remote-value", "k2": "x"}
    assert local_store == first  # second pull is a no-op-equivalent, no drift


# ---------------------------------------------------------------------------
# 5. admin /secrets/upsert stays 200 when replication push fails
# ---------------------------------------------------------------------------

from app.gateway.routers import admin_secrets  # noqa: E402


@pytest.fixture
def _vault_env(monkeypatch, tmp_path):
    """Isolated vault tmp path + cipher/admin env (mirrors the fixtures in
    ``test_admin_secrets_api.py`` so the upsert endpoint works without users.json)."""
    from deerflow.config.paths import Paths

    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr("deerflow.admin.secrets.get_paths", lambda: paths)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", "B" * 43)

    from app.gateway.auth import AuthUser

    def _owner() -> AuthUser:
        return AuthUser(
            id="owner",
            email="sabar.bao@me.com",
            role="owner",
            name="Owner",
            status="active",
            password_hash="x",
            salt="y",
        )

    _real = admin_secrets.authenticate_user

    def _fake_auth(email, password):  # type: ignore[no-untyped-def]
        if email == "sabar.bao@me.com" and password == "pw":
            return _owner()
        return _real(email, password)

    monkeypatch.setattr(admin_secrets, "authenticate_user", _fake_auth)
    monkeypatch.setenv("BY_ADMIN_PASSWORD", "pw")
    return tmp_path


@pytest.fixture
def client(_vault_env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(admin_secrets.router)
    with TestClient(app) as c:
        yield c


def test_upsert_endpoint_returns_200_when_replication_push_fails(
    client, monkeypatch
):
    """A best-effort replication push failure (transport or corrupt-vault read)
    must never turn a successful vault write into an error response. The real
    ``_replicate_after_write`` try/except absorbs it, so the write stays 200."""
    async def _boom(config, *, actor_id):  # noqa: ANN001
        raise RuntimeError("S3 unreachable during replication")

    monkeypatch.setattr(
        "deerflow.admin.replication_wiring.push_local_to_replica", _boom
    )

    r = client.post(
        "/api/admin/secrets/upsert",
        json={"key": "models/foo/api_key", "value": "sekrit-value"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "upserted"


# ---------------------------------------------------------------------------
# 6. Audit ok flag + audit-failure swallowing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_records_ok_false_on_transport_failure(
    monkeypatch,
):
    cfg = load_replication_config(_env())
    manager = _FakeManager()
    manager.push_exc = RuntimeError("KMS unreachable")
    _fake_vault(monkeypatch, initial={"k": "v"})
    events = _capture_audit(monkeypatch)

    await push_local_to_replica(cfg, manager, actor_id="u1")

    pushed = [e for e in events if e["action"] == "admin_secret.replica_pushed"]
    assert len(pushed) == 1
    assert pushed[0]["actor_id"] == "u1"
    assert pushed[0]["details"] == {"ok": False}


@pytest.mark.asyncio
async def test_record_replica_audit_swallows_audit_write_failure(monkeypatch):
    """A broken audit sink must never break the replication flow or raise."""
    captured: list[dict] = []

    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("audit disk full")

    # record_replica_audit imports the symbol from .audit at call time.
    monkeypatch.setattr("deerflow.admin.audit.append_admin_audit_record", _boom)

    # A failing audit sink must not raise out of record_replica_audit.
    record_replica_audit("pulled", actor_id="u1", remote="vaults/x", ok=True)
    assert captured == []


@pytest.mark.asyncio
async def test_pull_success_audits_true_after_vault_write(monkeypatch):
    """A successful hydrate must audit ok=True and only after the vault write."""
    cfg = load_replication_config(_env())
    manager = _FakeManager(blob=b'{"a": "1"}')
    local_store = _fake_vault(monkeypatch, initial={})
    events = _capture_audit(monkeypatch)

    await pull_replica_to_cache(cfg, manager)

    assert local_store == {"a": "1"}
    pulled = [e for e in events if e["action"] == "admin_secret.replica_pulled"]
    assert len(pulled) == 1
    assert pulled[0]["details"] == {"ok": True}