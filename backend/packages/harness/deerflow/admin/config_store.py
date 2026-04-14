from __future__ import annotations

import json
from threading import Lock

from pydantic import BaseModel, Field

from deerflow.admin.secrets import is_secret_ref, mask_secret_value, upsert_secret
from deerflow.config.paths import get_paths

_config_lock = Lock()
_cached_config: "AdminConfig | None" = None


class AdminTracingProviderConfig(BaseModel):
    enabled: bool = False
    api_key: str | None = None
    public_key: str | None = None
    secret_key: str | None = None
    project: str | None = None
    endpoint: str | None = None
    host: str | None = None


class AdminTracingConfig(BaseModel):
    langsmith: AdminTracingProviderConfig = Field(default_factory=AdminTracingProviderConfig)
    langfuse: AdminTracingProviderConfig = Field(default_factory=AdminTracingProviderConfig)


class AdminBrandingConfig(BaseModel):
    name: str = "MicX"
    short_name: str = "MicX"
    tagline: str = "面向个人与团队协作的中文智能服务工作台。"
    description: str = "MicX 是一个面向个人与团队协作的中文智能服务工作台。"
    support_email: str = "sabar.bao@me.com"
    website_path: str = "/"
    docs_path: str = "/zh/docs"


class AdminSystemConfig(BaseModel):
    log_level: str | None = None
    token_usage_enabled: bool | None = None


class AdminConfig(BaseModel):
    system: AdminSystemConfig = Field(default_factory=AdminSystemConfig)
    tracing: AdminTracingConfig = Field(default_factory=AdminTracingConfig)
    branding: AdminBrandingConfig = Field(default_factory=AdminBrandingConfig)

    def masked(self) -> "AdminConfig":
        data = self.model_copy(deep=True)
        data.tracing.langsmith.api_key = mask_secret_value(data.tracing.langsmith.api_key)
        data.tracing.langfuse.public_key = mask_secret_value(data.tracing.langfuse.public_key)
        data.tracing.langfuse.secret_key = mask_secret_value(data.tracing.langfuse.secret_key)
        return data


class AdminConfigUpdate(AdminConfig):
    pass


def _config_path():
    return get_paths().admin_config_file


def _persistable(config: AdminConfig) -> dict:
    current = _read_admin_config()
    data = config.model_dump(mode="json")
    langsmith_api = data["tracing"]["langsmith"].get("api_key")
    current_langsmith_api = current.tracing.langsmith.api_key
    if langsmith_api == mask_secret_value(current_langsmith_api):
        data["tracing"]["langsmith"]["api_key"] = current_langsmith_api
    if langsmith_api and not langsmith_api.startswith("$") and not is_secret_ref(langsmith_api):
        data["tracing"]["langsmith"]["api_key"] = upsert_secret("tracing/langsmith/api_key", langsmith_api)

    langfuse_public = data["tracing"]["langfuse"].get("public_key")
    current_langfuse_public = current.tracing.langfuse.public_key
    if langfuse_public == mask_secret_value(current_langfuse_public):
        data["tracing"]["langfuse"]["public_key"] = current_langfuse_public
    if langfuse_public and not langfuse_public.startswith("$") and not is_secret_ref(langfuse_public):
        data["tracing"]["langfuse"]["public_key"] = upsert_secret("tracing/langfuse/public_key", langfuse_public)

    langfuse_secret = data["tracing"]["langfuse"].get("secret_key")
    current_langfuse_secret = current.tracing.langfuse.secret_key
    if langfuse_secret == mask_secret_value(current_langfuse_secret):
        data["tracing"]["langfuse"]["secret_key"] = current_langfuse_secret
    if langfuse_secret and not langfuse_secret.startswith("$") and not is_secret_ref(langfuse_secret):
        data["tracing"]["langfuse"]["secret_key"] = upsert_secret("tracing/langfuse/secret_key", langfuse_secret)

    return data


def _read_admin_config() -> AdminConfig:
    path = _config_path()
    if not path.exists():
        return AdminConfig()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AdminConfig.model_validate(payload)


def get_admin_config() -> AdminConfig:
    global _cached_config
    if _cached_config is None:
        with _config_lock:
            if _cached_config is None:
                _cached_config = _read_admin_config()
    return _cached_config


def reload_admin_config() -> AdminConfig:
    global _cached_config
    with _config_lock:
        _cached_config = _read_admin_config()
        return _cached_config


def save_admin_config(config: AdminConfig) -> AdminConfig:
    global _cached_config
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _persistable(config)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    with _config_lock:
        _cached_config = AdminConfig.model_validate(payload)
    return _cached_config
