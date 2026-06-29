"""Tests for the built-in connector registration helper."""
from __future__ import annotations

import pytest

from app.gateway.connectors.dingtalk.connector import DingTalkConnector
from app.gateway.connectors.email.connector import EmailConnector
from app.gateway.connectors.feishu.connector import FeishuConnector
from app.gateway.connectors.integrations.builtin import register_builtin_connectors
from app.gateway.connectors.registry import ConnectorRegistry
from app.gateway.connectors.wecom.connector import WeComConnector


def test_empty_config_registers_nothing():
    reg = ConnectorRegistry()
    register_builtin_connectors(registry=reg, config={})
    assert reg.list_names() == []


def test_feishu_only_config_registers_feishu():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"feishu": {"app_id": "cli_x", "app_secret": "sec_x"}},
    )
    assert "feishu" in reg.list_names()
    assert isinstance(reg.get("feishu"), FeishuConnector)


def test_dingtalk_only_config_registers_dingtalk():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"dingtalk": {"client_id": "cid", "client_secret": "csec"}},
    )
    assert "dingtalk" in reg.list_names()
    assert isinstance(reg.get("dingtalk"), DingTalkConnector)


def test_wecom_only_config_registers_wecom():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"wecom": {"bot_id": "bid", "bot_secret": "bsec"}},
    )
    assert "wecom" in reg.list_names()
    assert isinstance(reg.get("wecom"), WeComConnector)


def test_email_only_config_registers_email():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={
            "email": {
                "smtp_host": "smtp.x",
                "smtp_port": 587,
                "smtp_user": "u",
                "smtp_password": "p",
                "imap_host": "imap.x",
                "imap_port": 993,
                "from_address": "bot@x",
            }
        },
    )
    assert "email" in reg.list_names()
    assert isinstance(reg.get("email"), EmailConnector)


def test_all_four_configured():
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={
            "feishu": {"app_id": "a", "app_secret": "b"},
            "dingtalk": {"client_id": "c", "client_secret": "d"},
            "wecom": {"bot_id": "e", "bot_secret": "f"},
            "email": {
                "smtp_host": "s",
                "smtp_port": 587,
                "smtp_user": "u",
                "smtp_password": "p",
                "imap_host": "i",
                "imap_port": 993,
                "from_address": "from@x",
            },
        },
    )
    assert set(reg.list_names()) == {"feishu", "dingtalk", "wecom", "email"}


def test_unknown_vendor_ignored():
    """A vendor without a built-in adapter is silently ignored."""
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"slack": {"bot_token": "x"}},  # no built-in slack yet
    )
    assert reg.list_names() == []


def test_partial_config_for_vendor_does_not_register():
    """If a required credential is missing, the connector is skipped (not raised)."""
    reg = ConnectorRegistry()
    register_builtin_connectors(
        registry=reg,
        config={"feishu": {"app_id": "a"}},  # missing app_secret
    )
    assert "feishu" not in reg.list_names()
