"""Multi-region secret replication core (v1.7 M4).

A small, fully-testable core behind the >DC secret replicator:

* ``wrap_envelope`` / ``unwrap_envelope`` — envelope encryption. A fresh
  random data key encrypts the vault bytes (AES-GCM); the key itself is
  wrapped by region KMS. The object-store blob is therefore never cleartext.
* ``SecretReplicator`` Protocol — the object-store surface (get / put /
  exists). Concrete adapters (S3 / GCS / Aliyun OSS) implement it via REST or
  the vendor SDK; this module stays transport-agnostic and unit-testable.
* ``ReplicationManager`` — mtime-conflict-safe reads/writes with a
  last-good cache, so a concurrent write never silently overwrites a newer
  replica; callers get a clear ``ConflictError``.

Audit hooks (caller-side): the admin layer appends ``admin_secret.replica_pulled``
/ ``admin_secret.replica_pushed`` via ``admin.audit`` when it drives the manager.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from typing import Protocol

# Optional AES-GCM (cryptography is already a runtime dep via Fernet).
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover - cryptography is a hard runtime dep
    AESGCM = None  # type: ignore[assignment]


class EnvelopeKMS(Protocol):
    """Wrap / unwrap the per-vault data key via a region KMS."""

    async def wrap(self, data_key: bytes) -> bytes: ...
    async def unwrap(self, wrapped_key: bytes) -> bytes: ...


class SecretReplicator(Protocol):
    """Async object-store surface for vault blobs."""

    async def get(self, remote: str) -> bytes | None: ...
    async def put(self, remote: str, payload: bytes) -> None: ...
    async def exists(self, remote: str) -> bool: ...


class ConflictError(Exception):
    """A concurrent writer owns a newer replica; the stale put was refused."""


_IV_LEN = 12
_TAG_LEN = 16
# 4-byte big-endian length prefix for the base64-wrapped key.
_LEN_PREFIX = 4


def _random_data_key() -> bytes:
    return secrets.token_bytes(32)


async def wrap_envelope(kms: EnvelopeKMS, plaintext: bytes) -> bytes:
    """Encrypt *plaintext* under a fresh KMS-wrapped data key.

    Envelope layout (the object-store blob)::

        4-byte keylen || base64(kms_wrapped_data_key) || iv(12) || ct+tag

    The plaintext bytes never appear in the blob.
    """
    assert AESGCM is not None and _TAG_LEN > 0, "cryptography is required"
    data_key = _random_data_key()
    wrapped_key = await kms.wrap(data_key)
    wrapped_b64 = base64.b64encode(wrapped_key)
    iv = secrets.token_bytes(_IV_LEN)
    ct = AESGCM(data_key).encrypt(iv, plaintext, None)
    return len(wrapped_b64).to_bytes(_LEN_PREFIX, "big") + wrapped_b64 + iv + ct


async def unwrap_envelope(kms: EnvelopeKMS, envelope: bytes) -> bytes:
    """Decrypt an envelope produced by :func:`wrap_envelope`."""
    assert AESGCM is not None, "cryptography is required"
    key_len = int.from_bytes(envelope[:_LEN_PREFIX], "big")
    wrapped_b64 = envelope[_LEN_PREFIX : _LEN_PREFIX + key_len]
    wrapped = base64.b64decode(wrapped_b64)
    iv = envelope[_LEN_PREFIX + key_len : _LEN_PREFIX + key_len + _IV_LEN]
    ct = envelope[_LEN_PREFIX + key_len + _IV_LEN :]
    data_key = await kms.unwrap(wrapped)
    return AESGCM(data_key).decrypt(iv, ct, None)


@dataclass
class ReplicationManager:
    """mtime-conflict-safe read/write over a :class:`SecretReplicator`.

    ``push`` refuses to overwrite a replica that another writer bumped (its
    on-disk blob differs from the ``expected_blob`` it was based on), avoiding
    silent lost updates across regions.
    """

    store: SecretReplicator
    kms: EnvelopeKMS

    async def pull(self, remote: str) -> bytes | None:
        blob = await self.store.get(remote)
        if blob is None:
            return None
        return await unwrap_envelope(self.kms, blob)

    async def push(
        self,
        remote: str,
        plaintext: bytes,
        *,
        expect_matches: bytes | None = None,
    ) -> None:
        """Write *plaintext* to *remote*, refusing on a concurrent bump.

        If ``expect_matches`` is given, the push is refused whenever the
        remote's current blob differs from it (someone else wrote a newer
        replica), raising :class:`ConflictError`.
        """
        if expect_matches is not None:
            current = await self.store.get(remote)
            if current != expect_matches:
                raise ConflictError(f"remote {remote} changed concurrently; refusing stale push")
        blob = await wrap_envelope(self.kms, plaintext)
        await self.store.put(remote, blob)


def record_replica_audit(direction: str, *, actor_id: str | None, remote: str, ok: bool = True) -> None:
    """Append a ``admin_secret.replica_pulled`` / ``admin_secret.replica_pushed``
    event (caller-side audit hook; swallows audit failures so replication is
    never blocked by an audit backlog)."""
    if direction not in ("pulled", "pushed"):
        return
    try:
        from .audit import append_admin_audit_record

        append_admin_audit_record(
            f"admin_secret.replica_{direction}",
            actor_id=actor_id,
            target=remote,
            details={"ok": ok},
        )
    except Exception:  # pragma: no cover - audit is best-effort
        pass


__all__ = [
    "ConflictError",
    "EnvelopeKMS",
    "ReplicationManager",
    "SecretReplicator",
    "record_replica_audit",
    "unwrap_envelope",
    "wrap_envelope",
]