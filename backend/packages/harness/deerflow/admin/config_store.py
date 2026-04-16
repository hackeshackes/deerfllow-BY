from __future__ import annotations

import json
from threading import Lock

from pydantic import BaseModel, Field

from deerflow.admin.secrets import is_secret_ref, mask_secret_value, upsert_secret
from deerflow.config.paths import get_paths

_config_lock = Lock()
_cached_config: AdminConfig | None = None


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


class AdminUploadConfig(BaseModel):
    max_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum upload file size in MB")
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".jpg", ".png"],
        description="Allowed file extensions for upload",
    )
    convert_to_markdown: bool = Field(default=True, description="Automatically convert files to markdown")


class AdminSandboxConfig(BaseModel):
    use: str = Field(default="deerflow.sandbox.local:LocalSandboxProvider", description="Sandbox provider class path")
    allow_host_bash: bool = Field(default=False, description="Allow host bash execution")
    bash_output_max_chars: int = Field(default=20000, ge=0, description="Max chars for bash output")
    read_file_output_max_chars: int = Field(default=50000, ge=0, description="Max chars for read_file output")
    ls_output_max_chars: int = Field(default=20000, ge=0, description="Max chars for ls output")


class AdminModelConfig(BaseModel):
    name: str = Field(..., description="Model name identifier")
    display_name: str = Field(..., description="Display name for UI")
    description: str | None = Field(default=None, description="Model description")
    use: str = Field(..., description="Model provider class path")
    model: str = Field(..., description="Model name for API")
    api_key: str | None = Field(default=None, description="API key (encrypted)")
    api_base: str | None = Field(default=None, description="API base URL")
    request_timeout: float = Field(default=600.0, description="Request timeout in seconds")
    max_retries: int = Field(default=2, ge=0, description="Maximum retry attempts")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    supports_vision: bool = Field(default=False, description="Whether model supports vision")
    supports_thinking: bool = Field(default=False, description="Whether model supports thinking mode")
    supports_reasoning_effort: bool = Field(default=False, description="Whether model supports reasoning effort")
    is_default: bool = Field(default=False, description="Is this the default model")
    use_responses_api: bool = Field(default=False, description="Use OpenAI Responses API")
    output_version: str | None = Field(default=None, description="Structured output version")
    thinking: dict | None = Field(default=None, description="Thinking configuration")
    when_thinking_enabled: dict | None = Field(default=None, description="Settings when thinking is enabled")


class AdminToolConfig(BaseModel):
    name: str = Field(..., description="Tool name")
    group: str = Field(..., description="Tool group")
    use: str = Field(..., description="Tool implementation class path")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    extra_params: dict = Field(default_factory=dict, description="Additional tool parameters")


class AdminSkillConfig(BaseModel):
    auto_update: bool = Field(default=False, description="Auto-update skills")
    security_scan: bool = Field(default=True, description="Scan skills for security")


class AdminMCPServerConfig(BaseModel):
    name: str = Field(..., description="MCP server name")
    type: str = Field(default="stdio", description="Transport type: stdio, sse, or http")
    command: str = Field(..., description="Command to start MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    url: str | None = Field(default=None, description="MCP server URL for sse/http type")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers for sse/http type")
    description: str = Field(default="", description="Human-readable description")
    enabled: bool = Field(default=True, description="Whether MCP server is enabled")


class AdminConfig(BaseModel):
    system: AdminSystemConfig = Field(default_factory=AdminSystemConfig)
    tracing: AdminTracingConfig = Field(default_factory=AdminTracingConfig)
    branding: AdminBrandingConfig = Field(default_factory=AdminBrandingConfig)
    upload: AdminUploadConfig = Field(default_factory=AdminUploadConfig)
    sandbox: AdminSandboxConfig = Field(default_factory=AdminSandboxConfig)
    models: list[AdminModelConfig] = Field(default_factory=list)
    tools: list[AdminToolConfig] = Field(default_factory=list)
    skills: AdminSkillConfig = Field(default_factory=AdminSkillConfig)
    mcp: list[AdminMCPServerConfig] = Field(default_factory=list)

    def masked(self) -> AdminConfig:
        data = self.model_copy(deep=True)
        data.tracing.langsmith.api_key = mask_secret_value(data.tracing.langsmith.api_key)
        data.tracing.langfuse.public_key = mask_secret_value(data.tracing.langfuse.public_key)
        data.tracing.langfuse.secret_key = mask_secret_value(data.tracing.langfuse.secret_key)
        # Mask model API keys
        for model in data.models:
            model.api_key = mask_secret_value(model.api_key) if model.api_key else None
        return data


class AdminConfigUpdate(AdminConfig):
    pass


def _config_path():
    return get_paths().admin_config_file


def _persistable(config: AdminConfig) -> dict:
    current = _read_admin_config()
    data = config.model_dump(mode="json")

    # Handle LangSmith API key
    langsmith_api = data["tracing"]["langsmith"].get("api_key")
    current_langsmith_api = current.tracing.langsmith.api_key
    if langsmith_api == mask_secret_value(current_langsmith_api):
        data["tracing"]["langsmith"]["api_key"] = current_langsmith_api
    if langsmith_api and not langsmith_api.startswith("$") and not is_secret_ref(langsmith_api):
        data["tracing"]["langsmith"]["api_key"] = upsert_secret("tracing/langsmith/api_key", langsmith_api)

    # Handle Langfuse public key
    langfuse_public = data["tracing"]["langfuse"].get("public_key")
    current_langfuse_public = current.tracing.langfuse.public_key
    if langfuse_public == mask_secret_value(current_langfuse_public):
        data["tracing"]["langfuse"]["public_key"] = current_langfuse_public
    if langfuse_public and not langfuse_public.startswith("$") and not is_secret_ref(langfuse_public):
        data["tracing"]["langfuse"]["public_key"] = upsert_secret("tracing/langfuse/public_key", langfuse_public)

    # Handle Langfuse secret key
    langfuse_secret = data["tracing"]["langfuse"].get("secret_key")
    current_langfuse_secret = current.tracing.langfuse.secret_key
    if langfuse_secret == mask_secret_value(current_langfuse_secret):
        data["tracing"]["langfuse"]["secret_key"] = current_langfuse_secret
    if langfuse_secret and not langfuse_secret.startswith("$") and not is_secret_ref(langfuse_secret):
        data["tracing"]["langfuse"]["secret_key"] = upsert_secret("tracing/langfuse/secret_key", langfuse_secret)

    # Handle model API keys
    for i, model in enumerate(data.get("models", [])):
        model_api_key = model.get("api_key")
        if model_api_key and model_api_key != mask_secret_value(""):
            current_model = next((m for m in current.models if m.name == model.get("name")), None)
            current_api_key = current_model.api_key if current_model else None
            if model_api_key == mask_secret_value(current_api_key or ""):
                data["models"][i]["api_key"] = current_api_key
            elif model_api_key and not model_api_key.startswith("$") and not is_secret_ref(model_api_key):
                data["models"][i]["api_key"] = upsert_secret(f"model/{model.get('name')}/api_key", model_api_key)

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
