"""Bridge between the admin secrets vault and the replication manager (v1.7 M4).

The replication core (``replication.py``) is transport-agnostic and has no
caller. This module is that caller: it maps the local vault's read/write path
(``_read_secret_map`` / ``_write_secret_map``) onto the manager's ``pull`` /
``push`` so the admin layer can:

* cold-start bootstrap: ``pull_replica_to_cache`` pulls the remote replica and
  hydrates the local vault (read path);
* propagate a local write: ``push_local_to_replica`` uploads the vault after a
  rotate / upsert (write path).

Both are best-effort: a disabled config, a missing object-store, or a KMS
failure must never break the existing degrade-to-empty read path.
"""

from __future__ import annotations

import json
import logging

from .replication import EnvelopeKMS, ReplicationManager, SecretReplicator, record_replica_audit
from .replication_config import ReplicationConfig
from .secrets import _read_secret_map, _write_secret_map

logger = logging.getLogger(__name__)


def _manager_for(config: ReplicationConfig) -> ReplicationManager | None:
    """Build a manager from the resolved config, or ``None`` when unusable."""
    if (
        not config.enabled
        or not config.region
        or not config.bucket
        or not config.remote
        or not config.access_key
        or not config.secret_key
        or not config.kms_key_id
    ):
        return None

    from .aws_kms import KMSEnvelope
    from .s3_replicator import S3Replicator

    store: SecretReplicator = S3Replicator(
        endpoint=config.endpoint or f"https://s3.{config.region}.amazonaws.com",
        bucket=config.bucket,
        region=config.region,
        access_key=config.access_key,
        secret_key=config.secret_key,
        readonly=config.readonly,
    )
    kms: EnvelopeKMS = KMSEnvelope(
        region=config.region,
        access_key=config.access_key,
        secret_key=config.secret_key,
        key_id=config.kms_key_id,
    )
    return ReplicationManager(store=store, kms=kms)


def build_rep_manager(config: ReplicationConfig) -> ReplicationManager | None:
    """Public factory for tests / callers that want the assembled manager."""
    return _manager_for(config)


async def pull_replica_to_cache(
    config: ReplicationConfig, manager: ReplicationManager | None = None
) -> None:
    """Hydrate the local vault from the remote replica (best-effort).

    Called at startup. Non-fatal: on any error we log and leave the local
    vault (and the degraded empty read path) untouched.
    """
    if not config.enabled or not config.remote:
        return
    mgr = manager or _manager_for(config)
    if mgr is None:
        return
    try:
        plaintext = await mgr.pull(config.remote)
    except Exception as exc:  # noqa: BLE001 — replication is non-critical at cold start
        record_replica_audit("pulled", actor_id=None, remote=config.remote, ok=False)
        logger.warning("secret replication pull failed for %s: %s", config.remote, exc)
        return
    if plaintext is None:
        return
    try:
        data = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("replica payload invalid for %s: %s", config.remote, exc)
        record_replica_audit("pulled", actor_id=None, remote=config.remote, ok=False)
        return
    if not isinstance(data, dict):
        logger.warning("replica payload not an object for %s", config.remote)
        return
    _write_secret_map({str(k): str(v) for k, v in data.items()})
    record_replica_audit("pulled", actor_id=None, remote=config.remote, ok=True)


async def push_local_to_replica(
    config: ReplicationConfig,
    manager: ReplicationManager | None = None,
    *,
    actor_id: str | None = None,
) -> None:
    """Propagate the local vault to the remote replica (best-effort).

    Called after a rotate / upsert. The pushed plaintext is the vault's JSON
    dict; the manager wraps it in a KMS-envelope before storage, so the
    object-store blob is never cleartext.
    """
    if not config.enabled or not config.remote:
        return
    mgr = manager or _manager_for(config)
    if mgr is None:
        return
    data = _read_secret_map()
    plaintext = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    try:
        await mgr.push(config.remote, plaintext)
    except Exception as exc:  # noqa: BLE001 — replication failure is non-critical
        logger.warning("secret replication push failed for %s: %s", config.remote, exc)
        record_replica_audit("pushed", actor_id=actor_id, remote=config.remote, ok=False)
        return
    record_replica_audit("pushed", actor_id=actor_id, remote=config.remote, ok=True)


__all__ = ["build_rep_manager", "pull_replica_to_cache", "push_local_to_replica"]