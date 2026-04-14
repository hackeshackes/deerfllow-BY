from __future__ import annotations

from deerflow.admin import config_store as config_store_module
from deerflow.admin import secrets as secrets_module
from deerflow.config.paths import Paths


def _patch_paths(monkeypatch, tmp_path):
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr(secrets_module, "get_paths", lambda: paths)
    monkeypatch.setattr(config_store_module, "get_paths", lambda: paths)
    monkeypatch.setattr(config_store_module, "_cached_config", None)


def test_secret_store_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-secret")
    _patch_paths(monkeypatch, tmp_path)

    ref = secrets_module.upsert_secret("models/demo/api_key", "sk-demo-secret")

    assert ref == "secret://models/demo/api_key"
    assert secrets_module.resolve_secret_ref(ref) == "sk-demo-secret"
    assert secrets_module.mask_secret_value(ref) == "••••••••"


def test_admin_config_persists_secret_refs(monkeypatch, tmp_path):
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-secret")
    _patch_paths(monkeypatch, tmp_path)

    config = config_store_module.AdminConfigUpdate(
        system={"log_level": "debug", "token_usage_enabled": True},
        tracing={
            "langsmith": {
                "enabled": True,
                "api_key": "lsv2-secret",
                "project": "micx",
                "endpoint": "https://smith.example.com",
            },
            "langfuse": {
                "enabled": True,
                "public_key": "pk-secret",
                "secret_key": "sk-secret",
                "host": "https://langfuse.example.com",
            },
        },
        branding={
            "name": "MicX",
            "short_name": "MicX",
            "tagline": "tagline",
            "description": "desc",
            "support_email": "ops@example.com",
            "website_path": "/",
            "docs_path": "/docs",
        },
    )

    saved = config_store_module.save_admin_config(config)
    paths = Paths(base_dir=tmp_path)
    stored = paths.admin_config_file.read_text(encoding="utf-8")

    assert "lsv2-secret" not in stored
    assert "pk-secret" not in stored
    assert "sk-secret" not in stored
    assert "secret://tracing/langsmith/api_key" in stored
    assert saved.tracing.langsmith.api_key == "secret://tracing/langsmith/api_key"
    assert saved.masked().tracing.langsmith.api_key == "••••••••"
