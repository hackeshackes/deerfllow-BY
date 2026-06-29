"""YAML config schema validation for connectors.

The schema is intentionally minimal: a connector config is a YAML mapping with
required `name` / `type` / `enabled` / `credentials` keys, optional `routes`,
and `type` drawn from a fixed whitelist of supported vendors.

Heavier validation (per-type credential shape, route patterns) lives in the
connector implementations themselves — this module only catches the structural
errors a human will hit most often when editing YAML by hand.
"""
from __future__ import annotations

from typing import Any

SUPPORTED_TYPES: frozenset[str] = frozenset(
    {"feishu", "dingtalk", "wecom", "email", "slack", "jira", "linear"}
)
"""Vendor types that have a registered connector implementation.

Note: jira/linear are reserved for v1.6.0 but the type is accepted here so
configs can be loaded in advance without schema churn.
"""


class ConfigError(ValueError):
    """Raised when a connector config fails structural validation."""


_REQUIRED_TOP_LEVEL: tuple[str, ...] = ("name", "type", "enabled", "credentials")


def validate_config(cfg: Any) -> None:
    """Validate a parsed YAML config dict. Raises ConfigError on issue.

    The validator is forgiving: it only enforces the small set of rules that
    catch the most common authoring mistakes. Anything more specific
    (per-vendor credential shape, route pattern syntax) is delegated to the
    individual connector's `from_config()` constructor.
    """
    if not isinstance(cfg, dict):
        raise ConfigError(f"config must be a mapping, got {type(cfg).__name__}")

    for required in _REQUIRED_TOP_LEVEL:
        if required not in cfg:
            raise ConfigError(f"missing required field: {required!r}")

    name = cfg["name"]
    if not isinstance(name, str) or not name.strip():
        raise ConfigError("name must be a non-empty string")

    type_ = cfg["type"]
    if not isinstance(type_, str):
        raise ConfigError("type must be a string")
    if type_ not in SUPPORTED_TYPES:
        raise ConfigError(
            f"unknown type: {type_!r}; supported: {sorted(SUPPORTED_TYPES)}"
        )

    enabled = cfg["enabled"]
    if not isinstance(enabled, bool):
        raise ConfigError(f"enabled must be a boolean, got {type(enabled).__name__}")

    credentials = cfg["credentials"]
    if not isinstance(credentials, dict):
        raise ConfigError("credentials must be a mapping")

    if "routes" in cfg:
        routes = cfg["routes"]
        if not isinstance(routes, list):
            raise ConfigError(f"routes must be a list, got {type(routes).__name__}")
        for i, route in enumerate(routes):
            if not isinstance(route, dict):
                raise ConfigError(f"routes[{i}] must be a mapping")
