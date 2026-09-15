"""Tests for the v1.9 M2 model auto-discovery: inspect / SSE inference / SSRF guard.

Covers the three producer protocols (OpenAI-compatible, Anthropic, Google Gemini),
capability inference from model id, the SSRF block-list on base_url, and the
owner-gated HTTP endpoint. No real network calls: discovery funcs take an
injected httpx client.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from deerflow.models.discovery import (
    DiscoveryResult,
    SSRFError,
    discover_for_provider,
    infer_capabilities,
    validate_discovery_url,
)

# ---------------------------------------------------------------------------
# Fake httpx client / response
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, payload: Any, code: int = 200) -> None:
        self._payload = payload
        self.status_code = code

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    """Minimal stand-in for httpx.AsyncClient capturing url+headers."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.closed = True  # matches `async with_client()` close contract

    async def __aenter__(self):  # pragma: no cover
        return self

    async def __aexit__(self, *exc):  # pragma: no cover
        self.closed = True

    async def get(self, url: str, *, params=None, headers=None, timeout=None, auth=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if self.responses:
            r = self.responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        return _FakeResp({}, 200)


# ---------------------------------------------------------------------------
# validate_discovery_url — SSRF guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "https://api.deepseek.com",
        "http://localhost:11434",
        "http://127.0.0.1:8000",
    ],
)
def test_validate_accepts_public_and_localhost(url: str) -> None:
    assert validate_discovery_url(url) == url.rstrip("/")


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",  # cloud metadata
        "http://10.0.0.5/v1",                       # private RFC1918
        "http://192.168.1.10/v1",                   # private RFC1918
        "http://172.16.0.1/v1",                    # private RFC1918
        "http://",                                  # not a host
        "not-a-url",
        "",
    ],
)
def test_validate_rejects_ssrf_and_invalid(url: str) -> None:
    with pytest.raises(SSRFError):
        validate_discovery_url(url)


# ---------------------------------------------------------------------------
# infer_capabilities heuristic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_id, vision, thinking",
    [
        ("gpt-4o-2024-08-06", True, False),
        ("gpt-4.1", True, False),
        ("claude-4-5-sonnet-20250912", True, True),
        ("claude-3-7-sonnet", False, True),
        ("gemini-2.5-pro", True, True),
        ("deepseek-r1", False, True),
        ("qwen3-max", False, True),
        ("kimi-k2-thinking", False, True),
        ("text-embedding-3-small", False, False),
    ],
)
def test_infer_capabilities(model_id: str, vision: bool, thinking: bool) -> None:
    v, t = infer_capabilities(model_id)
    assert v == vision, f"{model_id} vision"
    assert t == thinking, f"{model_id} thinking"


# ---------------------------------------------------------------------------
# OpenAI-compatible discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_compatible_discovery_returns_normalized_models() -> None:
    payload = {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "owned_by": "openai"},
            {"id": "text-embedding-3-small", "owned_by": "openai"},
        ],
    }
    client = FakeClient([_FakeResp(payload)])
    models = await discover_for_provider(
        provider="openai", api_key="sk-x", base_url="https://api.openai.com/v1", client=client
    )
    ids = [m.id for m in models]
    assert ids == ["gpt-4o", "text-embedding-3-small"]
    # vision inference applied
    gpt4o = next(m for m in models if m.id == "gpt-4o")
    assert gpt4o.supports_vision is True
    # request used the correct bearer auth endpoint
    req = client.calls[-1]
    assert req["url"].endswith("/models")
    assert req["headers"].get("authorization") == "Bearer sk-x"


@pytest.mark.asyncio
async def test_anthropic_discovery_uses_apikey_header() -> None:
    payload = {
        "data": [
            {"id": "claude-4-5-sonnet-20250912", "type": "model", "display_name": "Claude 4.5 Sonnet"},
            {"id": "claude-3-7-sonnet-latest", "type": "model"},
        ]
    }
    client = FakeClient([_FakeResp(payload)])
    models = await discover_for_provider(
        provider="anthropic", api_key="sk-ant-abc", base_url=None, client=client
    )
    assert [m.id for m in models] == ["claude-4-5-sonnet-20250912", "claude-3-7-sonnet-latest"]
    req = client.calls[-1]
    assert "anthropic" in req["url"]
    assert req["headers"].get("x-api-key") == "sk-ant-abc"
    assert req["headers"].get("anthropic-version")
    sonnet = next(m for m in models if m.id.startswith("claude-4"))
    assert sonnet.supports_vision is True


@pytest.mark.asyncio
async def test_gemini_discovery_uses_key() -> None:
    payload = {
        "models": [
            {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    client = FakeClient([_FakeResp(payload)])
    models = await discover_for_provider(
        provider="gemini", api_key="AIza…", base_url=None, client=client
    )
    assert [m.id for m in models] == ["gemini-2.5-pro", "gemini-2.5-flash"]
    req = client.calls[-1]
    assert "generativelanguage" in req["url"]
    assert req["headers"].get("x-goog-api-key") == "AIza…"


@pytest.mark.asyncio
async def test_unknown_provider_falls_back_to_empty() -> None:
    models = await discover_for_provider(
        provider="unsupported-thing", api_key="", base_url="https://x.com", client=FakeClient([])
    )
    assert models == []


@pytest.mark.asyncio
async def test_network_error_returns_discovery_result_error() -> None:

    client = FakeClient([RuntimeError("boom")])
    result = await DiscoveryResult.from_provider(
        provider="openai", api_key="k", base_url="https://api.openai.com/v1", client=client
    )
    assert result.discovered is False
    assert result.models == []
    assert result.error_message

# ---------------------------------------------------------------------------
# HTTP endpoint integration
# ---------------------------------------------------------------------------


def _owner_user():
    from app.gateway.auth import AuthUser

    return AuthUser(
        id="owner",
        email="sabar.bao@me.com",
        role="owner",
        name="Owner",
        status="active",
        password_hash="x",
        salt="y",
    )


def _member_user():
    from app.gateway.auth import AuthUser

    return AuthUser(id="m1", email="m@x.com", role="member", name="M", status="active", password_hash="x", salt="y")


async def _fake_from_provider(provider, api_key, base_url, client=None):
    from deerflow.models.discovery import DiscoveredModel

    return [
        DiscoveredModel("gpt-4o", "GPT-4o", supports_vision=True, supports_thinking=False),
        DiscoveredModel("deepseek-chat", "DeepSeek Chat", supports_vision=False, supports_thinking=True),
    ]


@pytest.fixture
def model_app():
    from fastapi import FastAPI

    from app.gateway.routers.models import router

    app = FastAPI()
    app.include_router(router)
    return app


def test_inspect_owner_returns_discovered_models(model_app) -> None:
    from fastapi.testclient import TestClient

    with patch("app.gateway.auth.session_user_from_request", return_value=_owner_user()), (
        patch("deerflow.models.discovery.discover_for_provider", new=_fake_from_provider)
    ):
        client = TestClient(model_app)
        r = client.post(
            "/api/admin/models/inspect",
            json={"provider": "openai", "base_url": "https://api.openai.com/v1", "api_key": "sk-x"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["discovered"] is True
    assert [m["id"] for m in body["models"]] == ["gpt-4o", "deepseek-chat"]
    assert body["models"][0]["supports_vision"] is True


def test_inspect_rejects_non_owner(model_app) -> None:
    from fastapi.testclient import TestClient

    with patch("app.gateway.auth.session_user_from_request", return_value=_member_user()):
        client = TestClient(model_app)
        r = client.post("/api/admin/models/inspect", json={"provider": "openai", "base_url": "https://api.openai.com/v1"})
    assert r.status_code == 403


def test_inspect_network_failure_degrades(model_app) -> None:
    from fastapi.testclient import TestClient

    async def _boom(*a, **k):
        raise RuntimeError("upstream unreachable")

    with patch("app.gateway.auth.session_user_from_request", return_value=_owner_user()), (
        patch("deerflow.models.discovery.discover_for_provider", new=_boom)
    ):
        client = TestClient(model_app)
        r = client.post("/api/admin/models/inspect", json={"provider": "anthropic", "api_key": "sk-ant-x"})
    assert r.status_code == 200
    assert r.json()["discovered"] is False
    assert r.json()["fallback_presets"] is True
