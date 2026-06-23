import os
from app.gateway.identity.config import IdentityConfig, get_identity_config

def test_default_config_disables_oidc():
    cfg = IdentityConfig()
    assert cfg.oidc_enabled is False
    assert cfg.audit_retention_days == 365
    assert cfg.scim_sync_interval_minutes == 60

def test_get_identity_config_caches():
    cfg1 = get_identity_config()
    cfg2 = get_identity_config()
    assert cfg1 is cfg2

def test_config_from_env(monkeypatch):
    monkeypatch.setenv("MICX_OIDC_ENABLED", "true")
    monkeypatch.setenv("MICX_AUDIT_RETENTION_DAYS", "90")
    cfg = IdentityConfig.from_env()
    assert cfg.oidc_enabled is True
    assert cfg.audit_retention_days == 90