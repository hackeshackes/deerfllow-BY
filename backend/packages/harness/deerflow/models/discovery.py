"""Model auto-discovery (closing-plan M2).

Given a provider base URL + API key, enumerate the models a backing gateway
actually accepts and infer their capabilities, so an operator can one-click
configure a model instead of hand-filling provider fields.

Three producer protocols:

* ``openai``  — OpenAI Chat Completions-compatible ``GET {base}/models``
  (OpenAI, DeepSeek, Qwen/Alibaba, Moonshot, vLLM, Ollama at ``/v1``, …).
* ``anthropic`` — Anthropic ``GET {base}/v1/models``.
* ``gemini``  — Google ``generativelanguage`` ``GET /v1beta/models``.

All outbound HTTP goes through an injectable ``httpx.AsyncClient`` so unit
tests never touch the network. Every base URL is SSRF-guarded before any call.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"
ANTHROPIC_DEFAULT_BASE = "https://api.anthropic.com"
GEMINI_DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


class DiscoveryError(Exception):
    """Raised when a discovery call materially fails (network, access, bad input)."""


class SSRFError(ValueError):
    """Raised when a candidate base URL is not safe to connect to."""


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    display_name: str | None = None
    supports_vision: bool = False
    supports_thinking: bool = False


@dataclass
class DiscoveryResult:
    provider: str
    base_url: str | None
    discovered: bool
    models: list[DiscoveredModel] = field(default_factory=list)
    error_message: str | None = None
    fallback_presets: bool = False

    @classmethod
    async def from_provider(
        cls,
        provider: str,
        api_key: str,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        try:
            models = await discover_for_provider(provider, api_key, base_url, client)
            return cls(
                provider=provider,
                base_url=base_url,
                discovered=True,
                models=models,
                fallback_presets=not models,
            )
        except Exception as exc:  # noqa: BLE001 — degrade, never fail the request
            return cls(
                provider=provider,
                base_url=base_url,
                discovered=False,
                models=[],
                error_message=str(exc),
                fallback_presets=True,
            )


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------


def validate_discovery_url(url: str) -> str:
    """Return ``url`` (trailing slash stripped) or raise :class:`SSRFError`.

    Allows https URLs and http to explicit local hosts (localhost / 127.0.0.1).
    Private / loopback / link-local / reserved host *literals* are rejected so a
    discovery probe can't be turned into an SSRF primitive.
    """
    if not url or not isinstance(url, str):
        raise SSRFError("base_url is required")
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise SSRFError("base_url must be http(s)")
    host = (parts.hostname or "").strip().lower()
    if not host:
        raise SSRFError("base_url has no host")
    if host in _LOCALHOST_HOSTS:
        return url.strip().rstrip("/")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # A domain name — can't resolve DNS here; treat as allowed.
        return url.strip().rstrip("/")
    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    ):
        raise SSRFError(f"base_url host '{host}' is not a reachable public host")
    return url.strip().rstrip("/")


def _resolve_base(url: str | None, default: str) -> str:
    return validate_discovery_url(url or default)


# ---------------------------------------------------------------------------
# Capability inference (naming heuristics; operators can override in the UI)
# ---------------------------------------------------------------------------

_VISION_MARKERS = (
    "gpt-4o", "gpt-4.1", "gpt-5", "claude-4",
    "gemini-2.5", "gemini-3", "omni", "vision", "multimodal", "llava",
)
_THINKING_MARKERS = (
    "claude-4", "claude-3-7", "gemini-2.5",
    "o1-", "o3-", "o4-", "reasoning",
    "deepseek-r1", "deepseek-r2", "qwen3", "thinking",
    "glm-4.6", "glm-5",
)
_EMBEDDING_MARKERS = ("embedding", "rerank", "text-embedding", "m3e")


def infer_capabilities(model_id: str) -> tuple[bool, bool]:
    """Return ``(supports_vision, supports_thinking)`` for a model id."""
    m = (model_id or "").lower()
    if any(t in m for t in _EMBEDDING_MARKERS):
        return False, False
    vision = any(t in m for t in _VISION_MARKERS)
    thinking = any(t in m for t in _THINKING_MARKERS)
    return vision, thinking


# ---------------------------------------------------------------------------
# Protocol implementations
# ---------------------------------------------------------------------------


async def _get_json(
    client: httpx.AsyncClient, url: str, headers: dict[str, str]
) -> dict[str, Any]:
    resp = await client.get(url, headers=headers, timeout=10.0)
    if resp.status_code >= 400:
        raise DiscoveryError(f"HTTP {resp.status_code} from {url}")
    return resp.json()


async def _discover_openai(
    client: httpx.AsyncClient, api_key: str, base: str
) -> list[DiscoveredModel]:
    url = f"{base}/models"
    data = await _get_json(client, url, {"authorization": f"Bearer {api_key}"})
    out: list[DiscoveredModel] = []
    for item in data.get("data") or []:
        mid = str(item.get("id", ""))
        if not mid:
            continue
        vision, thinking = infer_capabilities(mid)
        out.append(DiscoveredModel(mid, mid, vision, thinking))
    return out


async def _discover_anthropic(
    client: httpx.AsyncClient, api_key: str, base: str
) -> list[DiscoveredModel]:
    url = f"{base}/v1/models" if not base.endswith("/v1") else f"{base}/models"
    data = await _get_json(
        client, url, {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    )
    out: list[DiscoveredModel] = []
    for item in data.get("data") or []:
        mid = str(item.get("id", ""))
        if not mid:
            continue
        vision, thinking = infer_capabilities(mid)
        out.append(
            DiscoveredModel(
                mid,
                item.get("display_name") or mid,
                vision,
                thinking,
            )
        )
    return out


async def _discover_gemini(
    client: httpx.AsyncClient, api_key: str, base: str
) -> list[DiscoveredModel]:
    url = f"{base}/models"
    data = await _get_json(client, url, {"x-goog-api-key": api_key})
    out: list[DiscoveredModel] = []
    for item in data.get("models") or []:
        mid = str(item.get("name", "")).replace("models/", "", 1)
        if not mid:
            continue
        vision, thinking = infer_capabilities(mid)
        out.append(DiscoveredModel(mid, mid, vision, thinking))
    return out


async def discover_for_provider(
    provider: str,
    api_key: str,
    base_url: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[DiscoveredModel]:
    """Return discovered models, or [] for an unsupported provider."""
    own = client is None
    client = client or httpx.AsyncClient()
    try:
        p = (provider or "").lower()
        if p in ("openai", "openai-compatible", "openai-compat"):
            return await _discover_openai(client, api_key, _resolve_base(base_url, OPENAI_DEFAULT_BASE))
        if p == "anthropic":
            return await _discover_anthropic(client, api_key, _resolve_base(base_url, ANTHROPIC_DEFAULT_BASE))
        if p == "gemini":
            return await _discover_gemini(client, api_key, _resolve_base(base_url, GEMINI_DEFAULT_BASE))
        return []
    finally:
        if own:
            try:
                await client.aclose()
            except Exception:  # pragma: no cover
                pass