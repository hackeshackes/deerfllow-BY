"""Identity subsystem configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class IdentityConfig:
    """Configuration for identity subsystem.

    Reads from environment variables prefixed with MICX_*.
    """
    oidc_enabled: bool = False
    oidc_default_provider: str | None = None
    rbac_enabled: bool = True
    audit_enabled: bool = True
    audit_retention_days: int = 365
    audit_async_batch_size: int = 100
    scim_enabled: bool = False
    scim_sync_interval_minutes: int = 60

    @classmethod
    def from_env(cls) -> "IdentityConfig":
        return cls(
            oidc_enabled=os.getenv("MICX_OIDC_ENABLED", "false").lower() == "true",
            oidc_default_provider=os.getenv("MICX_OIDC_DEFAULT_PROVIDER"),
            rbac_enabled=os.getenv("MICX_RBAC_ENABLED", "true").lower() == "true",
            audit_enabled=os.getenv("MICX_AUDIT_ENABLED", "true").lower() == "true",
            audit_retention_days=int(os.getenv("MICX_AUDIT_RETENTION_DAYS", "365")),
            audit_async_batch_size=int(os.getenv("MICX_AUDIT_BATCH_SIZE", "100")),
            scim_enabled=os.getenv("MICX_SCIM_ENABLED", "false").lower() == "true",
            scim_sync_interval_minutes=int(os.getenv("MICX_SCIM_INTERVAL_MIN", "60")),
        )


@lru_cache(maxsize=1)
def get_identity_config() -> IdentityConfig:
    """Singleton accessor for IdentityConfig."""
    return IdentityConfig.from_env()