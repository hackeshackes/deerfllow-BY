from __future__ import annotations

import json
from enum import StrEnum
from threading import Lock
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from deerflow.admin.secrets import is_secret_ref, mask_secret_value, upsert_secret
from deerflow.config.paths import get_paths

_config_lock = Lock()
_cached_config: AdminConfig | None = None


class ModelVendor(StrEnum):
    """Catalog of supported model vendors.

    Adding a new vendor here is intentionally additive: existing configs that
    do not declare a vendor default to ``ModelVendor.OPENAI_COMPATIBLE`` so the
    field stays backwards compatible with the pre-hardening configs.
    """

    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    VOLCENGINE = "volcengine"
    ALIYUN = "aliyun"
    MOONSHOT = "moonshot"
    CODEX = "codex"  # ChatGPT Codex Responses API
    VLLM = "vllm"  # OpenAI-compatible self-hosted


VendorName = Literal[
    "openai",
    "openai_compatible",
    "azure_openai",
    "anthropic",
    "google",
    "mistral",
    "deepseek",
    "qwen",
    "volcengine",
    "aliyun",
    "moonshot",
    "codex",
    "vllm",
]


class ModelCapability(BaseModel):
    """Boolean flags advertising what a model can do.

    Each flag corresponds to a runtime capability checked by the agent router
    before invoking the underlying provider. The flags are derived from the
    vendor's published model card at registration time and may be overridden
    per-model.
    """

    model_config = ConfigDict(extra="forbid")

    text: bool = True
    vision: bool = False
    audio_in: bool = False
    audio_out: bool = False
    video_in: bool = False
    tool_use: bool = True
    parallel_tool_use: bool = False
    structured_output: bool = True
    json_schema: bool = False
    prompt_caching: bool = False  # Anthropic-style 5m/1h cache_control
    prompt_cache_key: bool = False  # allow per-cache-key routing
    web_search: bool = False
    computer_use: bool = False
    image_generation: bool = False
    file_search: bool = False
    code_execution: bool = False
    context_management: bool = False  # Anthropic context_management edits
    thinking: bool = False  # extended thinking / reasoning tokens
    reasoning_effort: bool = False  # OpenAI o-series reasoning_effort
    reasoning_content: bool = False  # DeepSeek reasoning_content field
    thought_signature: bool = False  # Google Gemini thought signatures
    skills: bool = False  # Anthropic Skills / container skill refs


class ThinkingConfig(BaseModel):
    """Vendor-agnostic thinking configuration.

    Each provider maps these fields onto its own request payload:
    - Anthropic: ``thinking={"type": "enabled", "budget_tokens": N}``
    - OpenAI o-series / Codex: ``reasoning_effort="low|medium|high"``
    - Google Gemini: ``thinking_config.thinking_budget`` + ``include_thoughts``
    - DeepSeek: ``reasoning_content=True``
    - Qwen / vLLM: ``extra_body.chat_template_kwargs.enable_thinking=True``
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["enabled", "disabled", "adaptive"] = "enabled"
    budget_tokens: int | None = Field(default=None, ge=0, le=200_000)
    effort: Literal["minimal", "low", "medium", "high", "xhigh"] | None = None
    include_thoughts: bool = False
    return_reasoning: bool = True  # DeepSeek / o-series: stream reasoning_content back
    interleave_thinking: bool = False  # Gemini: interleaved thinking
    adaptive_budget: bool = False  # Gemini 2.5 adaptive thinking budget


class StopSequences(BaseModel):
    """Model-level stop sequences (provider-native)."""

    model_config = ConfigDict(extra="forbid")

    sequences: list[str] = Field(default_factory=list, max_length=8)


class GenerationParams(BaseModel):
    """Generation defaults surfaced in admin UI.

    Each field has a vendor fallback in ``vendor_profiles``; explicit values
    win, falling back to provider defaults only when unset.
    """

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1)  # Anthropic / Google / Mistral
    max_tokens: int = Field(default=4096, ge=1)
    stop: StopSequences = Field(default_factory=StopSequences)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    seed: int | None = Field(default=None, ge=0)
    response_format: Literal["text", "json_object", "json_schema"] = "text"
    json_schema: dict[str, Any] | None = None
    parallel_tool_calls: bool = False
    stream_options_include_usage: bool = True
    service_tier: Literal["auto", "default", "flex", "priority"] | None = None
    safety_settings: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AdminModelConfig(BaseModel):
    """Catalog entry for a single chat model.

    Backwards compatible: existing fields keep their meaning; new vendor /
    capability fields are additive and default to vendor-neutral values.
    """

    model_config = ConfigDict(extra="ignore")

    # ── Identity ─────────────────────────────────────────────────────────────
    name: str = Field(..., description="Model name identifier")
    display_name: str = Field(..., description="Display name for UI")
    description: str | None = Field(default=None, description="Model description")
    vendor: ModelVendor = Field(
        default=ModelVendor.OPENAI_COMPATIBLE,
        description="Model vendor. Determines which vendor-specific fields are honored at runtime.",
    )
    use: str = Field(..., description="Model provider class path")
    model: str = Field(..., description="Model name for API")

    # ── Auth / endpoint ──────────────────────────────────────────────────────
    api_key: str | None = Field(default=None, description="API key (encrypted)")
    api_base: str | None = Field(default=None, description="API base URL")
    api_version: str | None = Field(default=None, description="Azure / Google API version")
    organization: str | None = Field(default=None, description="OpenAI org header")
    project: str | None = Field(default=None, description="OpenAI project header")
    region: str | None = Field(default=None, description="AWS region (Bedrock / Vertex routing)")
    headers: dict[str, str] = Field(default_factory=dict, description="Extra HTTP headers")

    # ── Request defaults ─────────────────────────────────────────────────────
    request_timeout: float = Field(default=600.0, description="Request timeout in seconds")
    max_retries: int = Field(default=2, ge=0, description="Maximum retry attempts")
    generation: GenerationParams = Field(default_factory=GenerationParams)
    thinking: ThinkingConfig | None = Field(default=None, description="Thinking configuration")

    # ── Capability flags ─────────────────────────────────────────────────────
    capabilities: ModelCapability = Field(default_factory=ModelCapability)
    supports_vision: bool = Field(default=False, description="Whether model supports vision")
    supports_thinking: bool = Field(default=False, description="Whether model supports thinking mode")
    supports_reasoning_effort: bool = Field(default=False, description="Whether model supports reasoning effort")

    # ── Routing ─────────────────────────────────────────────────────────────
    is_default: bool = Field(default=False, description="Is this the default model")
    enabled: bool = Field(default=True, description="Whether the model is enabled")
    tier: Literal["primary", "secondary", "fallback"] = "primary"
    weight: int = Field(default=100, ge=1, le=1000, description="Routing weight for fallback pools")
    cost_per_1k_input: float | None = Field(default=None, ge=0)
    cost_per_1k_output: float | None = Field(default=None, ge=0)
    context_window: int | None = Field(default=None, ge=1, description="Max context tokens")

    # ── Vendor-specific flags (mapped onto provider kwargs) ───────────────────
    use_responses_api: bool = Field(default=False, description="Use OpenAI Responses API")
    use_chat_completions: bool = Field(default=False, description="Use OpenAI Chat Completions API explicitly")
    output_version: str | None = Field(default=None, description="Structured output version")
    when_thinking_enabled: dict[str, Any] | None = Field(default=None, description="Settings when thinking is enabled")

    # Anthropic-specific
    anthropic_beta: list[str] = Field(
        default_factory=list,
        description="Anthropic beta features (e.g. prompt-caching-2024-07-31, computer-use-2024-10-22, skills-2025-01-01)",
    )
    prompt_cache_retention: Literal["5m", "1h"] | None = None
    container_skills: list[str] = Field(
        default_factory=list,
        description="Anthropic container Skills references (skill://... or version refs)",
    )

    # Google Gemini-specific
    gemini_safety: list[dict[str, Any]] = Field(default_factory=list)
    gemini_thinking_budget: int | None = Field(default=None, ge=0, le=24576)
    gemini_thinking_include: bool = False

    # Qwen / vLLM-specific
    qwen_enable_thinking: bool | None = None  # explicit override of chat_template_kwargs

    # Codex Responses API
    codex_endpoint: Literal["responses", "chat"] = "responses"
    codex_store: bool = False

    # Legacy fast-path fields kept for back-compat
    legacy_thinking: dict[str, Any] | None = Field(default=None, exclude=True)


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
    """Branding strings rendered on the login page and homepage.

    All fields are sanitized at the model level to prevent persistent XSS:
      - max_length caps abuse
      - pattern rejects HTML / script-tag payloads; React will still render the
        string as text, but defense-in-depth here prevents accidental
        dangerouslySetInnerHTML on a future code path.
    """

    _SAFE_TEXT_PATTERN = r"^[^<>]*$"
    _MAX_LEN = 200

    name: str = Field(default="MicX", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    short_name: str = Field(default="MicX", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    tagline: str = Field(default="面向个人与团队协作的中文智能服务工作台。", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    description: str = Field(default="MicX 是一个面向个人与团队协作的中文智能服务工作台。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    support_email: str = Field(default="sabar.bao@me.com", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    website_path: str = Field(default="/", max_length=_MAX_LEN, pattern=r"^/[A-Za-z0-9_\-/{}]*$")
    docs_path: str = Field(default="/zh/docs", max_length=_MAX_LEN, pattern=r"^/[A-Za-z0-9_\-/{}]*$")
    # Login page
    login_badge: str = Field(default="中文优先 · 邀请制团队工作台", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    login_title: str = Field(default="登录 {name}", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    login_subtitle: str = Field(default="{name} 是一个面向个人与团队协作的中文智能服务工作台，适合研究、写作、文件分析和长任务执行。目前仅支持受邀账号登录使用。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    feature_title_1: str = Field(default="专注执行", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    feature_desc_1: str = Field(default="在一个空间里完成复杂任务、查看进度并沉淀结果。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    feature_title_2: str = Field(default="协作有边界", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    feature_desc_2: str = Field(default="支持个人空间与共享空间，适合私有部署和团队协作。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    # Homepage
    homepage_capabilities_title: str = Field(default="带上下文的研究能力", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_capabilities_desc: str = Field(default="在同一个空间中完成长链路研究、资料比对，并保留完整的对话和推理过程。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_capabilities_title_2: str = Field(default="围绕文件开展工作", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_capabilities_desc_2: str = Field(default="上传文档、分析内容，并把生成的产物与对话结果持续沉淀在一起。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_capabilities_title_3: str = Field(default="直接产出可交付结果", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_capabilities_desc_3: str = Field(default="无需切换工具，就能导出笔记、报告与各类可交付成果。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_workflow_1: str = Field(default="深度研究、调研纪要与结构化摘要", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_workflow_2: str = Field(default="文章、方案、规范与操作文档写作", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_workflow_3: str = Field(default="围绕上传文件、生成文件和导出的产物工作流", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_workflow_4: str = Field(default="带待办、进度与后续建议的长任务执行", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_why_title: str = Field(default="为什么选择 {name}", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_why_subtitle: str = Field(default="一个适合个人与团队协作的中文 AI 工作台。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_why_description: str = Field(default="{name} 把智能体执行、文件处理、结果产出与协作上下文放在同一个工作区中，让你和团队成员不用频繁切换工具，也能完成高质量工作流。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_scenarios_title: str = Field(default="适合的使用场景", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_team_title: str = Field(default="中文团队版", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)
    homepage_team_subtitle: str = Field(default="支持个人空间与团队空间并行协作。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_team_description: str = Field(default="保留个人记忆与个人智能体的私有边界，同时让共享空间里的对话、上传和产物真正服务于团队协作。如需帮助，请联系 {support_email}。", max_length=1000, pattern=_SAFE_TEXT_PATTERN)
    homepage_team_button: str = Field(default="联系 {name}", max_length=_MAX_LEN, pattern=_SAFE_TEXT_PATTERN)


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
