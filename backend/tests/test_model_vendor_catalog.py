"""Tests for the vendor-aware model factory catalog (2026 capabilities)."""

from __future__ import annotations

import pytest

from deerflow.admin.config_store import (
    AdminModelConfig,
    GenerationParams,
    ModelCapability,
    ModelVendor,
    StopSequences,
    ThinkingConfig,
)
from deerflow.config import app_config as app_config_module
from deerflow.config.model_config import ModelConfig
from deerflow.models import factory as factory_module
from deerflow.models.factory import (
    _VENDOR_PROFILES,
    create_chat_model,
    get_vendor_profile,
)

# ---------------------------------------------------------------------------
# AdminModelConfig schema
# ---------------------------------------------------------------------------


def test_admin_model_config_defaults_include_vendor_and_capabilities():
    config = AdminModelConfig(
        name="claude-sonnet",
        display_name="Claude Sonnet",
        use="langchain_anthropic:ChatAnthropic",
        model="claude-sonnet-4-6",
    )
    assert config.vendor == ModelVendor.OPENAI_COMPATIBLE
    assert config.capabilities.thinking is False
    assert config.capabilities.tool_use is True
    assert config.generation.max_tokens == 4096
    assert config.thinking is None
    assert config.tier == "primary"
    assert config.weight == 100
    assert config.enabled is True


def test_admin_model_config_supports_vendor_specific_fields():
    config = AdminModelConfig(
        name="qwen-max",
        display_name="Qwen3 Max",
        use="langchain_openai:ChatOpenAI",
        model="qwen3-max",
        vendor=ModelVendor.QWEN,
        capabilities=ModelCapability(thinking=True, vision=True),
        thinking=ThinkingConfig(type="enabled", budget_tokens=8192),
        generation=GenerationParams(
            temperature=0.4,
            top_p=0.95,
            top_k=40,
            max_tokens=16384,
            stop=StopSequences(sequences=["<|endoftext|>"]),
            parallel_tool_calls=True,
        ),
        qwen_enable_thinking=True,
        gemini_thinking_budget=4096,
        anthropic_beta=["prompt-caching-2024-07-31", "skills-2025-01-01"],
        container_skills=["skill://web-research/1.0"],
    )
    payload = config.model_dump()
    assert payload["vendor"] == "qwen"
    assert payload["capabilities"]["thinking"] is True
    assert payload["capabilities"]["vision"] is True
    assert payload["thinking"]["budget_tokens"] == 8192
    assert payload["generation"]["top_k"] == 40
    assert payload["qwen_enable_thinking"] is True
    assert payload["anthropic_beta"] == ["prompt-caching-2024-07-31", "skills-2025-01-01"]
    assert payload["container_skills"] == ["skill://web-research/1.0"]


def test_admin_model_config_vendor_enum_lists_known_providers():
    names = {member.value for member in ModelVendor}
    assert {"openai", "anthropic", "google", "deepseek", "qwen", "volcengine", "aliyun"} <= names


# ---------------------------------------------------------------------------
# Vendor profile catalog
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vendor, expected_keys",
    [
        (ModelVendor.OPENAI, {"temperature", "top_p", "reasoning_effort", "response_format"}),
        (ModelVendor.ANTHROPIC, {"temperature", "top_p", "top_k", "max_tokens", "thinking"}),
        (ModelVendor.GOOGLE, {"temperature", "thinking_config", "safety_settings"}),
        (ModelVendor.DEEPSEEK, {"reasoning_content", "tools", "tool_choice"}),
        (ModelVendor.QWEN, {"temperature", "extra_body", "tools"}),
        (ModelVendor.ALIYUN, {"temperature", "top_k", "thinking_budget"}),
        (ModelVendor.MOONSHOT, {"temperature", "tools", "tool_choice"}),
        (ModelVendor.VOLCENGINE, {"temperature", "thinking"}),
        (ModelVendor.VLLM, {"extra_body"}),
        (ModelVendor.CODEX, {"reasoning_effort", "store"}),
    ],
)
def test_vendor_profile_contains_expected_capabilities(vendor: str, expected_keys: set[str]) -> None:
    profile = get_vendor_profile(vendor)
    allowlist = profile["extra_kwargs_allowlist"]
    missing = expected_keys - allowlist
    assert not missing, f"Vendor {vendor} missing fields: {missing}"


def test_unknown_vendor_falls_back_to_openai_compatible():
    profile = get_vendor_profile("not-a-real-vendor")
    fallback = get_vendor_profile(ModelVendor.OPENAI_COMPATIBLE)
    assert profile["extra_kwargs_allowlist"] == fallback["extra_kwargs_allowlist"]


def test_every_supported_vendor_has_an_entry():
    """Catalog completeness: every vendor in ModelVendor has a profile."""
    for vendor in ModelVendor:
        assert vendor in _VENDOR_PROFILES, f"Vendor {vendor} missing from profile catalog"


# ---------------------------------------------------------------------------
# Factory: vendor-aware kwargs translation
# ---------------------------------------------------------------------------


class _CapturingModel:
    """BaseChatModel stub that records the kwargs it received."""

    captured: dict = {}

    def __init__(self, **kwargs):
        _CapturingModel.captured = dict(kwargs)
        # Skip pydantic validation; we only care about kwargs.


def _patch_factory(monkeypatch, app_config, model_class=_CapturingModel):
    monkeypatch.setattr(factory_module, "get_app_config", lambda: app_config)
    monkeypatch.setattr(factory_module, "resolve_class", lambda path, base: model_class)
    monkeypatch.setattr(factory_module, "build_tracing_callbacks", lambda: [])


def _make_app_config(models):
    return app_config_module.AppConfig(
        models=models,
        sandbox=app_config_module.SandboxConfig(use="deerflow.sandbox.local:LocalSandboxProvider"),
    )


def _make_model(name: str = "m", use: str = "langchain_openai:ChatOpenAI", vendor: str | None = None, **extras) -> ModelConfig:
    # Some flags are already on ModelConfig's schema; let callers override via
    # the keyword by suppressing the default value.
    defaults = dict(
        max_tokens=4096,
        supports_thinking=False,
        supports_reasoning_effort=False,
        when_thinking_enabled=None,
        thinking=None,
        supports_vision=False,
    )
    defaults.update(extras)
    # Pass vendor as an extra constructor field so it lands in model_extra.
    if vendor is not None:
        defaults.setdefault("vendor", vendor)
    return ModelConfig(
        name=name,
        display_name=name,
        description=None,
        use=use,
        model=name,
        **defaults,
    )


def test_factory_uses_vendor_default_api_base_for_anthropic(monkeypatch):
    cfg = _make_app_config([_make_model("claude-sonnet", use="langchain_anthropic:ChatAnthropic")])
    cfg.models[0].vendor = ModelVendor.ANTHROPIC  # type: ignore[attr-defined]
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="claude-sonnet")
    assert _CapturingModel.captured["base_url"] == "https://api.anthropic.com"


def test_factory_uses_vendor_default_api_base_for_qwen(monkeypatch):
    cfg = _make_app_config([_make_model("qwen", use="langchain_openai:ChatOpenAI")])
    cfg.models[0].vendor = ModelVendor.QWEN  # type: ignore[attr-defined]
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="qwen")
    assert _CapturingModel.captured["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_factory_drops_unknown_kwargs_for_openai(monkeypatch):
    """OpenAI vendor profile must reject ``extra_body`` even though it is generic."""
    cfg = _make_app_config([_make_model("gpt-5", use="langchain_openai:ChatOpenAI")])
    cfg.models[0].vendor = ModelVendor.OPENAI  # type: ignore[attr-defined]
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="gpt-5")
    assert "extra_body" not in _CapturingModel.captured


def test_factory_passes_extra_body_for_qwen(monkeypatch):
    cfg = _make_app_config(
        [
            _make_model(
                "qwen",
                use="langchain_openai:ChatOpenAI",
                thinking={"type": "enabled", "budget_tokens": 4096},
                supports_thinking=True,
                vendor=ModelVendor.QWEN,
            )
        ]
    )
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="qwen", thinking_enabled=True)
    extra_body = _CapturingModel.captured.get("extra_body", {})
    assert extra_body.get("chat_template_kwargs", {}).get("enable_thinking") is True


def test_factory_anthropic_beta_propagates(monkeypatch):
    cfg = _make_app_config(
        [
            _make_model(
                "claude",
                use="langchain_anthropic:ChatAnthropic",
                vendor=ModelVendor.ANTHROPIC,
            )
        ]
    )
    cfg.models[0].betas = ["prompt-caching-2024-07-31", "skills-2025-01-01"]  # type: ignore[attr-defined]
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="claude")
    assert "prompt-caching-2024-07-31" in _CapturingModel.captured["betas"]
    assert "skills-2025-01-01" in _CapturingModel.captured["betas"]


def test_factory_disable_path_keeps_reasoning_effort_minimal(monkeypatch):
    """OpenAI-compatible disable path must mirror the old behavior."""
    cfg = _make_app_config(
        [
            _make_model(
                "ow",
                use="langchain_openai:ChatOpenAI",
                when_thinking_enabled={"extra_body": {"thinking": {"type": "enabled", "budget_tokens": 1024}}},
                supports_thinking=True,
                supports_reasoning_effort=True,
                vendor=ModelVendor.OPENAI_COMPATIBLE,
            )
        ]
    )
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="ow", thinking_enabled=False)
    assert _CapturingModel.captured["extra_body"] == {"thinking": {"type": "disabled"}}
    assert _CapturingModel.captured["reasoning_effort"] == "minimal"


def test_factory_disable_anthropic_injects_disabled_thinking(monkeypatch):
    cfg = _make_app_config(
        [
            _make_model(
                "claude",
                use="langchain_anthropic:ChatAnthropic",
                thinking={"type": "enabled", "budget_tokens": 4096},
                supports_thinking=True,
                vendor=ModelVendor.ANTHROPIC,
            )
        ]
    )
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="claude", thinking_enabled=False)
    assert _CapturingModel.captured["thinking"] == {"type": "disabled"}


def test_factory_disable_vllm_injects_chat_template_kwargs(monkeypatch):
    cfg = _make_app_config(
        [
            _make_model(
                "vllm",
                use="langchain_openai:ChatOpenAI",
                thinking={"type": "enabled", "budget_tokens": 4096},
                supports_thinking=True,
                vendor=ModelVendor.VLLM,
            )
        ]
    )
    _patch_factory(monkeypatch, cfg)
    create_chat_model(name="vllm", thinking_enabled=False)
    chat_template = _CapturingModel.captured.get("extra_body", {}).get("chat_template_kwargs", {})
    assert chat_template.get("enable_thinking") is False


def test_factory_codex_strips_max_tokens(monkeypatch):
    from deerflow.models.openai_codex_provider import CodexChatModel

    captured: dict = {}

    class CapturingCodexModel(CodexChatModel):
        def __init__(self, **kwargs):
            captured.update(kwargs)
            # Skip pydantic validation; only inspect kwargs.

    cfg = _make_app_config(
        [
            _make_model(
                "codex",
                use="deerflow.models.openai_codex_provider:CodexChatModel",
                supports_reasoning_effort=True,
                vendor=ModelVendor.CODEX,
            )
        ]
    )
    _patch_factory(monkeypatch, cfg, model_class=CapturingCodexModel)
    create_chat_model(name="codex", thinking_enabled=False)
    assert captured.get("reasoning_effort") == "none"


def test_admin_config_supports_vendor_array_round_trip():
    """AdminModelConfig dump/load preserves vendor + capability flags."""
    config = AdminConfig(models=[admin_model("a")])
    round_tripped = AdminConfig.model_validate(config.model_dump())
    assert round_tripped.models[0].vendor == ModelVendor.QWEN
    assert round_tripped.models[0].capabilities.thinking is True
    assert round_tripped.models[0].generation.top_k == 40


def admin_model(name: str) -> AdminModelConfig:
    """Build a representative AdminModelConfig for round-trip tests."""
    return AdminModelConfig(
        name=name,
        display_name=name,
        use="langchain_openai:ChatOpenAI",
        model="qwen3-max",
        vendor=ModelVendor.QWEN,
        capabilities=ModelCapability(thinking=True, vision=True),
        generation=GenerationParams(top_k=40, max_tokens=8192, temperature=0.3),
        thinking=ThinkingConfig(type="enabled", budget_tokens=4096),
    )


# Late binding for the helper to reference AdminConfig
from deerflow.admin.config_store import AdminConfig  # noqa: E402  placed at module load for readability