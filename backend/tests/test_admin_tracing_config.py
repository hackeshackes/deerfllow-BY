from __future__ import annotations

from deerflow.admin.config_store import AdminConfig
from deerflow.config import tracing_config as tracing_module


def test_tracing_config_uses_admin_overrides(monkeypatch):
    tracing_module.reset_tracing_config()
    monkeypatch.setattr(
        tracing_module,
        "get_admin_config",
        lambda: AdminConfig.model_validate(
            {
                "tracing": {
                    "langsmith": {
                        "enabled": True,
                        "api_key": "secret://tracing/langsmith/api_key",
                        "project": "micx-project",
                        "endpoint": "https://smith.example.com",
                    },
                    "langfuse": {
                        "enabled": False,
                    },
                }
            }
        ),
    )
    monkeypatch.setattr(tracing_module, "resolve_secret_ref", lambda value: "lsv2-admin-key" if value else None)

    config = tracing_module.get_tracing_config()

    assert config.langsmith.enabled is True
    assert config.langsmith.api_key == "lsv2-admin-key"
    assert config.langsmith.project == "micx-project"
    assert config.enabled_providers == ["langsmith"]

    tracing_module.reset_tracing_config()
