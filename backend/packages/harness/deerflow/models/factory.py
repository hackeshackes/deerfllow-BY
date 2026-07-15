"""Factory that turns ``ModelConfig`` entries into instantiated chat models.

The factory merges per-model settings with a vendor profile so operators do not
need to hand-write vendor-specific kwargs. Vendor profiles are kept small and
documented inline. New vendors can be added by extending ``ModelVendor`` and
``_VENDOR_PROFILES``.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.chat_models import BaseChatModel

from deerflow.config import get_app_config
from deerflow.config.model_config import ModelConfig
from deerflow.reflection import resolve_class
from deerflow.tracing import build_tracing_callbacks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vendor enum + per-vendor profile catalog
# ---------------------------------------------------------------------------
# A profile lists (a) default kwargs that the underlying LangChain provider
# actually accepts and (b) the schema of fields the factory will translate.
# Anything outside the ``extra_kwargs_allowlist`` is dropped to keep the
# constructor surface clean.
# ---------------------------------------------------------------------------

class ModelVendor:
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
    CODEX = "codex"
    VLLM = "vllm"

    @classmethod
    def from_string(cls, value: str | None) -> str:
        if not value:
            return cls.OPENAI_COMPATIBLE
        lookup = {v for v in vars(cls).values() if isinstance(v, str)}
        return value if value in lookup else cls.OPENAI_COMPATIBLE


_VENDOR_PROFILES: dict[str, dict[str, Any]] = {
    ModelVendor.OPENAI: {
        "default_api_base": "https://api.openai.com/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "stop",
            "max_tokens",
            "parallel_tool_calls",
            "stream_options",
            "response_format",
            "service_tier",
            "metadata",
            "reasoning_effort",
            "logit_bias",
            "n",
            "user",
            "modalities",
            "audio",
            "prediction",
            "store",
            "truncation",
        },
    },
    ModelVendor.OPENAI_COMPATIBLE: {
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "response_format",
            "seed",
            "extra_body",
            "frequency_penalty",
            "presence_penalty",
            "tools",
            "tool_choice",
            # Many OpenAI-compatible gateways (vLLM, DeepSeek, Moonshot,
            # Qwen-compatible) accept the OpenAI ``reasoning_effort`` field.
            # Surfacing it from the disable path is what callers expect.
            "reasoning_effort",
        },
    },
    ModelVendor.AZURE_OPENAI: {
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "stop",
            "max_tokens",
            "response_format",
            "reasoning_effort",
        },
    },
    ModelVendor.ANTHROPIC: {
        "default_api_base": "https://api.anthropic.com",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
            "stop_sequences",
            "metadata",
            "thinking",
            "betas",
            "extra_headers",
            "context_management",
            "container",
        },
    },
    ModelVendor.GOOGLE: {
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "top_k",
            "max_output_tokens",
            "safety_settings",
            "thinking_config",
            "response_schema",
            "response_mime_type",
        },
    },
    ModelVendor.MISTRAL: {
        "default_api_base": "https://api.mistral.ai/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "random_seed",
            "response_format",
            "parallel_tool_calls",
            "tools",
            "tool_choice",
            "presence_penalty",
            "frequency_penalty",
            "prediction",
        },
    },
    ModelVendor.DEEPSEEK: {
        "default_api_base": "https://api.deepseek.com/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "max_tokens",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
            "logprobs",
            "top_logprobs",
            "reasoning_content",
        },
    },
    ModelVendor.QWEN: {
        "default_api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
            "extra_body",
        },
    },
    ModelVendor.VOLCENGINE: {
        "default_api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
            "thinking",
        },
    },
    ModelVendor.ALIYUN: {
        "default_api_base": "https://dashscope.aliyuncs.com/api/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
            "stop",
            "result_format",
            "tools",
            "tool_choice",
            "incremental_output",
            "thinking_budget",
        },
    },
    ModelVendor.MOONSHOT: {
        "default_api_base": "https://api.moonshot.cn/v1",
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "tools",
            "tool_choice",
            "response_format",
        },
    },
    ModelVendor.CODEX: {
        "default_api_base": "https://chatgpt.com/backend-api/codex",
        "extra_kwargs_allowlist": {
            "reasoning_effort",
            "store",
            "metadata",
            "endpoint_kind",
        },
    },
    ModelVendor.VLLM: {
        "extra_kwargs_allowlist": {
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "extra_body",
            "response_format",
        },
    },
}


def get_vendor_profile(vendor: str) -> dict[str, Any]:
    """Return the static capability profile for ``vendor``.

    Unknown vendors fall back to the OpenAI-compatible profile so the factory
    keeps producing a working model.
    """
    return _VENDOR_PROFILES.get(vendor, _VENDOR_PROFILES[ModelVendor.OPENAI_COMPATIBLE])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_merge_dicts(base: dict | None, override: dict) -> dict:
    """Recursively merge two dictionaries without mutating the inputs."""
    merged: dict[str, Any] = dict(base or {})
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _vllm_disable_chat_template_kwargs(chat_template_kwargs: dict) -> dict:
    """Build the disable payload for vLLM/Qwen chat template kwargs."""
    disable_kwargs: dict[str, bool] = {}
    if "thinking" in chat_template_kwargs:
        disable_kwargs["thinking"] = False
    if "enable_thinking" in chat_template_kwargs:
        disable_kwargs["enable_thinking"] = False
    return disable_kwargs


def _resolve_vendor(model_config: ModelConfig) -> str:
    """Resolve the vendor name from a ModelConfig (extra="allow" aware)."""
    extras = _resolve_extras(model_config)
    raw = extras.get("vendor")
    if raw is None:
        return ModelVendor.OPENAI_COMPATIBLE
    if isinstance(raw, ModelVendor):
        return raw.value if hasattr(raw, "value") else str(raw)
    return ModelVendor.from_string(raw)


def _resolve_extras(model_config: ModelConfig) -> dict[str, Any]:
    """Return all extra (non-schema) fields stored on the model."""
    extras = getattr(model_config, "model_extra", None)
    if extras:
        return dict(extras)
    # Fall back to scanning the model __dict__ for unknown keys.
    known = {f for f in ModelConfig.model_fields}
    return {k: v for k, v in model_config.__dict__.items() if k not in known and not k.startswith("_")}


def _build_provider_kwargs(model_config: ModelConfig, thinking_enabled: bool) -> dict[str, Any]:
    """Translate a ``ModelConfig`` into kwargs for the provider class."""
    vendor = _resolve_vendor(model_config)
    profile = get_vendor_profile(vendor)
    allowlist: set[str] = profile["extra_kwargs_allowlist"]
    extras = _resolve_extras(model_config)

    payload: dict[str, Any] = {
        "model": model_config.model,
        "max_tokens": model_config.max_tokens,
    }
    if model_config.temperature is not None and "temperature" in allowlist:
        payload["temperature"] = model_config.temperature
    if model_config.request_timeout:
        payload["timeout"] = model_config.request_timeout
    if model_config.max_retries is not None and "max_retries" in allowlist:
        payload["max_retries"] = model_config.max_retries
    # Surface base_url / api_key from the model schema (always accepted).
    if model_config.base_url:
        payload["base_url"] = model_config.base_url
    elif profile.get("default_api_base"):
        payload["base_url"] = profile["default_api_base"]
    if model_config.api_key:
        payload["api_key"] = model_config.api_key
    # Surface extras the operator added to the YAML — strictly allowlisted.
    for key in ("top_p", "top_k", "frequency_penalty", "presence_penalty", "seed", "stop"):
        if key in extras and key in allowlist:
            payload[key] = extras[key]
    if "response_format" in extras and "response_format" in allowlist:
        payload["response_format"] = extras["response_format"]
    if "reasoning_effort" in extras and "reasoning_effort" in allowlist:
        payload["reasoning_effort"] = extras["reasoning_effort"]
    # OpenAI Responses API routing flag is part of the original ModelConfig
    # schema (not an ``extra``). Pass it through when the vendor accepts it.
    use_responses_api = getattr(model_config, "use_responses_api", None)
    output_version = getattr(model_config, "output_version", None)
    if use_responses_api is not None:
        payload["use_responses_api"] = bool(use_responses_api)
    if output_version:
        payload["output_version"] = output_version
    # Vendor-specific extension buckets.
    if vendor == ModelVendor.ANTHROPIC and "betas" in extras and "betas" in allowlist:
        payload["betas"] = list(extras["betas"])
    if vendor in {ModelVendor.QWEN, ModelVendor.VLLM, ModelVendor.OPENAI_COMPATIBLE}:
        if "extra_body" in extras and "extra_body" in allowlist:
            payload["extra_body"] = dict(extras["extra_body"])
        if "thinking" in extras and isinstance(extras["thinking"], dict) and "thinking" in allowlist:
            payload["thinking"] = dict(extras["thinking"])

    # Thinking / reasoning
    has_wte = model_config.when_thinking_enabled is not None
    has_thinking_shortcut = model_config.thinking is not None
    if thinking_enabled and (has_wte or has_thinking_shortcut):
        if not model_config.supports_thinking:
            raise ValueError(
                f"Model {model_config.name} does not support thinking. "
                f"Set `supports_thinking` to true in the `config.yaml` to enable thinking."
            ) from None
        enable_payload = _build_enable_payload(model_config, vendor, allowlist)
        if enable_payload:
            payload = _deep_merge_dicts(payload, enable_payload)
    if not thinking_enabled and (has_wte or has_thinking_shortcut):
        if effective_wte_payload := _build_disable_payload(model_config, vendor, allowlist):
            payload = _deep_merge_dicts(payload, effective_wte_payload)
    if not model_config.supports_reasoning_effort:
        payload.pop("reasoning_effort", None)
    return payload


def _build_disable_payload(model_config: ModelConfig, vendor: str, allowlist: set[str]) -> dict[str, Any]:
    """Build the disable payload that mirrors the operator's enable payload."""
    effective_wte: dict[str, Any] = dict(model_config.when_thinking_enabled or {})
    if model_config.thinking is not None:
        effective_wte.setdefault("thinking", {}).update(dict(model_config.thinking))
    disable: dict[str, Any] = {}
    if effective_wte.get("extra_body", {}).get("thinking", {}).get("type"):
        # OpenAI-compatible gateway style: thinking nested in extra_body.
        disable["extra_body"] = {"thinking": {"type": "disabled"}}
        if "reasoning_effort" in allowlist:
            disable["reasoning_effort"] = "minimal"
    elif vendor in {ModelVendor.VLLM, ModelVendor.QWEN, ModelVendor.ALIYUN}:
        # vLLM / Qwen / Bailian accept thinking via chat_template_kwargs.
        # Even when the operator used the ``thinking`` shortcut, we know the
        # model is a chat-template one and the disable path must mirror that.
        existing = effective_wte.get("extra_body", {}).get("chat_template_kwargs") or {}
        disable_kwargs: dict[str, Any] = dict(existing)
        disable_kwargs["enable_thinking"] = False
        disable["extra_body"] = {"chat_template_kwargs": disable_kwargs}
        if "reasoning_effort" in allowlist:
            disable["reasoning_effort"] = "minimal"
    elif disable_chat_template_kwargs := _vllm_disable_chat_template_kwargs(
        effective_wte.get("extra_body", {}).get("chat_template_kwargs") or {}
    ):
        disable["extra_body"] = {"chat_template_kwargs": disable_chat_template_kwargs}
        if "reasoning_effort" in allowlist:
            disable["reasoning_effort"] = "minimal"
    elif effective_wte.get("thinking", {}).get("type"):
        # Native langchain_anthropic style: thinking is a direct constructor param.
        disable["thinking"] = {"type": "disabled"}
    return disable


def _build_enable_payload(model_config: ModelConfig, vendor: str, allowlist: set[str]) -> dict[str, Any]:
    """Build the enable payload that maps the operator's thinking config onto the vendor."""
    effective_wte: dict[str, Any] = dict(model_config.when_thinking_enabled or {})
    if model_config.thinking is not None:
        effective_wte.setdefault("thinking", {}).update(dict(model_config.thinking))
    if not effective_wte:
        return {}
    if vendor in {ModelVendor.VLLM, ModelVendor.QWEN, ModelVendor.ALIYUN}:
        # Map native ``thinking={type:enabled, budget_tokens:N}`` to chat_template_kwargs.
        thinking = effective_wte.get("thinking")
        if thinking and thinking.get("type") in {"enabled", "adaptive"} and "enable_thinking" not in effective_wte.get("extra_body", {}).get("chat_template_kwargs", {}):
            chat_kwargs = dict(effective_wte.get("extra_body", {}).get("chat_template_kwargs") or {})
            chat_kwargs["enable_thinking"] = True
            if "budget_tokens" in thinking and "thinking_budget" not in chat_kwargs:
                chat_kwargs["thinking_budget"] = thinking["budget_tokens"]
            new_extra_body = dict(effective_wte.get("extra_body") or {})
            new_extra_body["chat_template_kwargs"] = chat_kwargs
            # Drop the native ``thinking`` since vLLM doesn't accept it.
            return {"extra_body": new_extra_body}
    # Default path: pass the merged dict through (covers OpenAI Responses API,
    # Anthropic native, DeepSeek reasoning_content, Google thinking_config).
    return effective_wte


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_chat_model(name: str | None = None, thinking_enabled: bool = False, **kwargs: Any) -> BaseChatModel:
    """Create a chat model instance from the config.

    Args:
        name: The name of the model to create. If None, the first model in the
            config will be used.
        thinking_enabled: Whether to inject thinking-specific kwargs.

    Returns:
        A chat model instance.
    """
    config = get_app_config()
    if name is None:
        name = config.get_default_model_name()
    if name is None:
        raise ValueError("No chat models are configured. Please configure at least one model in config.yaml.")
    model_config = config.get_model_config(name)
    if model_config is None:
        raise ValueError(f"Model {name} not found in config") from None
    model_class = resolve_class(model_config.use, BaseChatModel)

    provider_kwargs = _build_provider_kwargs(model_config, thinking_enabled)

    # For Codex Responses API models: map thinking mode to reasoning_effort.
    from deerflow.models.openai_codex_provider import CodexChatModel

    if issubclass(model_class, CodexChatModel):
        # The ChatGPT Codex endpoint currently rejects max_tokens/max_output_tokens.
        provider_kwargs.pop("max_tokens", None)
        explicit_effort = kwargs.pop("reasoning_effort", None)
        if not thinking_enabled:
            provider_kwargs["reasoning_effort"] = "none"
        elif explicit_effort and explicit_effort in ("low", "medium", "high", "xhigh"):
            provider_kwargs["reasoning_effort"] = explicit_effort
        elif "reasoning_effort" not in provider_kwargs:
            provider_kwargs["reasoning_effort"] = "medium"

    model_instance = model_class(**kwargs, **provider_kwargs)

    callbacks = build_tracing_callbacks()
    if callbacks:
        existing_callbacks = getattr(model_instance, "callbacks", None) or []
        try:
            model_instance.callbacks = [*existing_callbacks, *callbacks]
            logger.debug(f"Tracing attached to model '{name}' with providers={len(callbacks)}")
        except AttributeError:
            logger.debug("Provider %s does not expose .callbacks; tracing not attached", model_class.__name__)
    return model_instance