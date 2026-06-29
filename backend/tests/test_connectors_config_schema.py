"""Tests for the YAML connector config schema validator."""
from __future__ import annotations

import pytest
import yaml

from app.gateway.connectors.config_schema import ConfigError, validate_config


def _parse(s: str) -> dict:
    return yaml.safe_load(s)


def test_valid_feishu_config():
    cfg = _parse("""
    name: feishu-prod
    type: feishu
    enabled: true
    credentials:
      app_id: cli_xxx
      app_secret: secret
    routes:
      - pattern: "thread.created"
        target:
          chat_id: oc_xxx
    """)
    validate_config(cfg)  # should not raise


def test_missing_name_raises():
    cfg = {"type": "feishu", "enabled": True, "credentials": {}}
    with pytest.raises(ConfigError, match="name"):
        validate_config(cfg)


def test_missing_type_raises():
    cfg = {"name": "x", "enabled": True, "credentials": {}}
    with pytest.raises(ConfigError, match="type"):
        validate_config(cfg)


def test_missing_enabled_raises():
    cfg = {"name": "x", "type": "feishu", "credentials": {}}
    with pytest.raises(ConfigError, match="enabled"):
        validate_config(cfg)


def test_missing_credentials_raises():
    cfg = {"name": "x", "type": "feishu", "enabled": True}
    with pytest.raises(ConfigError, match="credentials"):
        validate_config(cfg)


def test_invalid_type_raises():
    cfg = {"name": "x", "type": "unknown_vendor", "enabled": True, "credentials": {}}
    with pytest.raises(ConfigError, match="unknown type"):
        validate_config(cfg)


def test_valid_routes_optional():
    cfg = {
        "name": "x",
        "type": "feishu",
        "enabled": True,
        "credentials": {"app_id": "a", "app_secret": "b"},
    }
    validate_config(cfg)


def test_routes_must_be_list():
    cfg = {
        "name": "x",
        "type": "feishu",
        "enabled": True,
        "credentials": {},
        "routes": "not-a-list",
    }
    with pytest.raises(ConfigError, match="routes"):
        validate_config(cfg)


def test_credentials_must_be_mapping():
    cfg = {
        "name": "x",
        "type": "feishu",
        "enabled": True,
        "credentials": "not-a-mapping",
    }
    with pytest.raises(ConfigError, match="credentials"):
        validate_config(cfg)


def test_enabled_must_be_bool():
    cfg = {"name": "x", "type": "feishu", "enabled": "yes", "credentials": {}}
    with pytest.raises(ConfigError, match="enabled"):
        validate_config(cfg)


def test_config_must_be_mapping():
    with pytest.raises(ConfigError, match="mapping"):
        validate_config("not-a-dict")  # type: ignore[arg-type]


def test_email_type_accepted():
    cfg = {
        "name": "email-1",
        "type": "email",
        "enabled": True,
        "credentials": {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "u@x",
            "smtp_password": "p",
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "from_address": "bot@x",
        },
    }
    validate_config(cfg)
