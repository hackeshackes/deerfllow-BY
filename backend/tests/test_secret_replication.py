"""Tests for multi-region secret replication core (v1.7 M4).

Covers the fully unit-testable core behind the replicator:
1. Envelope encryption — a KMS-wrapped data key protects the vault; the
   object-store blob is never cleartext and round-trips un/decrypt.
2. Pull / push round-trip over a fake object store.
3. Conflict refusal — a push based on a stale expected blob is refused, so a
   concurrent writer's newer replica is never silently overwritten.
"""

from __future__ import annotations

import pytest

from deerflow.admin.replication import (
    ConflictError,
    ReplicationManager,
    unwrap_envelope,
    wrap_envelope,
)


class _FakeKMS:
    _SALT = bytes(range(32))  # exactly 32 bytes → deterministic XOR

    async def wrap(self, data_key: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(data_key, _FakeKMS._SALT))

    async def unwrap(self, wrapped: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(wrapped, _FakeKMS._SALT))


class _FakeStore:
    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}

    async def get(self, remote: str) -> bytes | None:
        return self.blobs.get(remote)

    async def put(self, remote: str, payload: bytes) -> None:
        self.blobs[remote] = payload

    async def exists(self, remote: str) -> bool:
        return remote in self.blobs


@pytest.mark.asyncio
async def test_envelope_hides_cleartext_and_round_trips():
    kms = _FakeKMS()
    plaintext = b'{"vault": 1}'
    envelope = await wrap_envelope(kms, plaintext)
    assert b"vault" not in envelope  # cleartext never in the blob
    assert await unwrap_envelope(kms, envelope) == plaintext


@pytest.mark.asyncio
async def test_same_payload_wraps_distinctly():
    kms = _FakeKMS()
    e1 = await wrap_envelope(kms, b"x")
    e2 = await wrap_envelope(kms, b"x")
    assert e1 != e2  # fresh data key per wrap


@pytest.mark.asyncio
async def test_replicator_round_trip():
    store = _FakeStore()
    repl = ReplicationManager(store=store, kms=_FakeKMS())
    remote = "vaults/primary/secrets.json"

    await repl.push(remote=remote, plaintext=b"hello")
    assert await store.exists(remote)
    assert await repl.pull(remote=remote) == b"hello"


@pytest.mark.asyncio
async def test_stale_push_refused_on_concurrent_write():
    store = _FakeStore()
    repl = ReplicationManager(store=store, kms=_FakeKMS())
    remote = "vaults/primary/secrets.json"

    # Writer A pushes v1.
    await repl.push(remote=remote, plaintext=b"v1")
    a_blob = await store.get(remote)
    assert a_blob is not None

    # Writer B (another region) bumps to v2.
    await repl.push(remote=remote, plaintext=b"v2")

    # Writer A retries its stale write based on the obsolete v1 blob → refused.
    with pytest.raises(ConflictError):
        await repl.push(remote=remote, plaintext=b"v1-again", expect_matches=a_blob)


@pytest.mark.asyncio
async def test_push_with_current_expected_succeeds():
    store = _FakeStore()
    repl = ReplicationManager(store=store, kms=_FakeKMS())
    remote = "vaults/primary/secrets.json"

    await repl.push(remote=remote, plaintext=b"v1")
    current = await store.get(remote)
    assert current is not None
    # A push based on the current blob (no concurrent bump) succeeds.
    await repl.push(remote=remote, plaintext=b"v2", expect_matches=current)
    assert await repl.pull(remote=remote) == b"v2"


def test_record_replica_audit_appends_event(monkeypatch):
    """The caller-side audit hook appends admin_secret.replica_* events."""
    from deerflow.admin import audit as audit_mod
    from deerflow.admin.replication import record_replica_audit

    events: list[dict] = []
    monkeypatch.setattr(
        audit_mod,
        "append_admin_audit_record",
        lambda action, *, actor_id=None, target="", details=None: events.append(
            {"action": action, "actor_id": actor_id, "target": target, "details": details}
        ),
    )

    record_replica_audit("pulled", actor_id="u1", remote="vaults/primary/secrets.json")
    record_replica_audit("pushed", actor_id="u1", remote="vaults/primary/secrets.json")

    assert [e["action"] for e in events] == [
        "admin_secret.replica_pulled",
        "admin_secret.replica_pushed",
    ]
    assert events[0]["target"] == "vaults/primary/secrets.json"
    assert events[0]["details"] == {"ok": True}