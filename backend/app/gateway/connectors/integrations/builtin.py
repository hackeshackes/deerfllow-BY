"""Register built-in connectors from a config dict.

`config` shape:
    {
        "feishu":   {"app_id": ..., "app_secret": ...},
        "dingtalk": {"client_id": ..., "client_secret": ...},
        "wecom":    {"bot_id": ..., "bot_secret": ...},
        "email":    {"smtp_host": ..., "smtp_port": ..., ...},
    }

Vendors that have no built-in adapter (e.g. slack) are silently skipped —
the caller can later attach a custom adapter via `registry.register(...)`.
A vendor whose required credentials are missing is also skipped, not raised;
this keeps a partially-completed config from breaking startup.
"""
from __future__ import annotations

import logging

from ..dingtalk.connector import DingTalkConnector
from ..email.connector import EmailConnector
from ..feishu.connector import FeishuConnector
from ..registry import ConnectorRegistry
from ..wecom.connector import WeComConnector

logger = logging.getLogger(__name__)


def register_builtin_connectors(registry: ConnectorRegistry, config: dict) -> None:
    if "feishu" in config:
        c = config["feishu"]
        if c.get("app_id") and c.get("app_secret"):
            registry.register(
                FeishuConnector(app_id=c["app_id"], app_secret=c["app_secret"])
            )
        else:
            logger.warning("feishu config missing app_id/app_secret; skipping")

    if "dingtalk" in config:
        c = config["dingtalk"]
        if c.get("client_id") and c.get("client_secret"):
            registry.register(
                DingTalkConnector(
                    client_id=c["client_id"], client_secret=c["client_secret"]
                )
            )
        else:
            logger.warning("dingtalk config missing client_id/client_secret; skipping")

    if "wecom" in config:
        c = config["wecom"]
        if c.get("bot_id") and c.get("bot_secret"):
            registry.register(
                WeComConnector(bot_id=c["bot_id"], bot_secret=c["bot_secret"])
            )
        else:
            logger.warning("wecom config missing bot_id/bot_secret; skipping")

    if "email" in config:
        c = config["email"]
        required = ("smtp_host", "smtp_port", "smtp_user", "smtp_password",
                    "imap_host", "imap_port", "from_address")
        if all(c.get(k) is not None for k in required):
            registry.register(
                EmailConnector(
                    smtp_host=c["smtp_host"],
                    smtp_port=c["smtp_port"],
                    smtp_user=c["smtp_user"],
                    smtp_password=c["smtp_password"],
                    imap_host=c["imap_host"],
                    imap_port=c["imap_port"],
                    from_address=c["from_address"],
                )
            )
        else:
            logger.warning("email config missing required fields; skipping")
