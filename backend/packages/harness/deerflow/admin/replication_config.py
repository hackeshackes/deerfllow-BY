"""Env-driven config for multi-region secret replication (v1.7 M4).

Reads the ``SECRETS_REPLICATION_*`` env surface into a frozen
:class:`ReplicationConfig`. Absent or non-``true`` ``ENABLED`` → a disabled
config (never raises); this keeps the cold-start / degradation path (no vault,
no object-store creds) identical to today.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

_ENV_TRUE = {"1", "true", "TRUE", "yes", "YES"}


@dataclass(frozen=True)
class ReplicationConfig:
    """Resolved multi-region replication settings; ``enabled=False`` is the no-op default."""

    enabled: bool = False
    region: str | None = None
    bucket: str | None = None
    remote: str | None = None
    endpoint: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    kms_key_id: str | None = None
    readonly: bool = False


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip() in _ENV_TRUE


def _expand_region(remote: str | None, region: str | None) -> str | None:
    """Substitute ``${REGION}`` in the remote key template."""
    if remote is None or region is None or "${REGION}" not in remote:
        return remote
    return remote.replace("${REGION}", region)


def load_replication_config(env: Mapping[str, str] | None = None) -> ReplicationConfig:
    """Parse replication config from ``env`` (default: ``os.environ``).

    No-op by default: only when ``SECRETS_REPLICATION_ENABLED`` is truthy does
    the rest become meaningful; a partial config stays disabled.
    """
    env_map = os.environ if env is None else env

    if not _as_bool(env_map.get("SECRETS_REPLICATION_ENABLED")):
        return ReplicationConfig()

    region = env_map.get("SECRETS_REPLICATION_REGION")
    remote = _expand_region(env_map.get("SECRETS_REPLICATION_REMOTE"), region)
    return ReplicationConfig(
        enabled=True,
        region=region,
        bucket=env_map.get("SECRETS_REPLICATION_BUCKET"),
        remote=remote,
        endpoint=env_map.get("SECRETS_REPLICATION_ENDPOINT"),
        access_key=env_map.get("SECRETS_REPLICATION_ACCESS_KEY"),
        secret_key=env_map.get("SECRETS_REPLICATION_SECRET_KEY"),
        kms_key_id=env_map.get("SECRETS_REPLICATION_KMS_KEY_ID"),
        readonly=_as_bool(env_map.get("SECRETS_REPLICATION_READONLY")),
    )


__all__ = ["ReplicationConfig", "load_replication_config"]