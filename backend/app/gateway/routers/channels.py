"""Gateway router for IM channel management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.gateway.auth import require_owner_user
from deerflow.config.app_config import AppConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])

SUPPORTED_CHANNEL_TYPES = {"feishu", "slack", "telegram", "wecom", "dingtalk"}


class ChannelStatusResponse(BaseModel):
    service_running: bool
    channels: dict[str, dict]


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


class ChannelConfigResponse(BaseModel):
    feishu: dict[str, Any] | None = None
    slack: dict[str, Any] | None = None
    telegram: dict[str, Any] | None = None
    wecom: dict[str, Any] | None = None
    dingtalk: dict[str, Any] | None = None


class ChannelUpdateRequest(BaseModel):
    enabled: bool | None = None
    # Feishu
    app_id: str | None = None
    app_secret: str | None = None
    # Slack
    bot_token: str | None = None
    app_token: str | None = None
    # Slack (legacy, migrate to app_token)
    team_id: str | None = None
    # WeCom
    bot_id: str | None = None
    bot_secret: str | None = None
    # WeCom (legacy, migrate to bot_id/bot_secret)
    corp_id: str | None = None
    agent_id: str | None = None
    corp_secret: str | None = None
    # DingTalk
    client_id: str | None = None
    client_secret: str | None = None


class ChannelConfigUpdateRequest(BaseModel):
    feishu: dict[str, Any] | None = None
    slack: dict[str, Any] | None = None
    telegram: dict[str, Any] | None = None
    wecom: dict[str, Any] | None = None
    dingtalk: dict[str, Any] | None = None


class ChannelThreadResponse(BaseModel):
    channel: str
    chat_id: str
    topic_id: str | None = None
    thread_id: str
    user_id: str
    micx_user_id: str | None = None
    micx_workspace_id: str | None = None
    created_at: float
    updated_at: float


class ChannelThreadsListResponse(BaseModel):
    channels: list[ChannelThreadResponse]


class ChannelThreadUpdateRequest(BaseModel):
    micx_user_id: str | None = None
    micx_workspace_id: str | None = None


def _get_channels_yaml_path() -> Path:
    return AppConfig.resolve_config_path()


def _load_channels_from_yaml() -> dict[str, Any]:
    config_path = _get_channels_yaml_path()
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("channels", {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_channels_to_yaml(channels_config: dict[str, Any]) -> None:
    config_path = _get_channels_yaml_path()
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            data = {}
        data["channels"] = channels_config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Failed to save channels config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save channels config: {e}")


@router.get("/", response_model=ChannelStatusResponse)
async def get_channels_status() -> ChannelStatusResponse:
    """Get the status of all IM channels."""
    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is None:
        return ChannelStatusResponse(service_running=False, channels={})
    status = service.get_status()
    return ChannelStatusResponse(**status)


@router.post("/{name}/restart", response_model=ChannelRestartResponse)
async def restart_channel(name: str) -> ChannelRestartResponse:
    """Restart a specific IM channel."""
    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Channel service is not running")

    success = await service.restart_channel(name)
    if success:
        logger.info("Channel %s restarted successfully", name)
        return ChannelRestartResponse(success=True, message=f"Channel {name} restarted successfully")
    else:
        logger.warning("Failed to restart channel %s", name)
        return ChannelRestartResponse(success=False, message=f"Failed to restart channel {name}")


@router.get("/config", response_model=ChannelConfigResponse)
async def get_channel_config(request: Request) -> ChannelConfigResponse:
    require_owner_user(request)
    from deerflow.config.app_config import get_app_config

    config = get_app_config()
    extra = config.model_extra or {}
    channels_config = extra.get("channels", {})

    return ChannelConfigResponse(
        feishu=channels_config.get("feishu"),
        slack=channels_config.get("slack"),
        telegram=channels_config.get("telegram"),
        wecom=channels_config.get("wecom"),
        dingtalk=channels_config.get("dingtalk"),
    )


@router.get("/feishu/messages", name="get_feishu_messages")
async def get_feishu_messages(
    chat_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    page_size: int = 20,
    request: Request = None,
) -> dict[str, Any]:
    require_owner_user(request)

    from deerflow.community.feishu_tools import feishu_get_messages

    result = feishu_get_messages.invoke(
        {
            "chat_id": chat_id,
            "start_time": start_time,
            "end_time": end_time,
            "page_size": page_size,
        }
    )
    return {"messages": result}


@router.get("/feishu/messages/{message_id}", name="get_feishu_message_by_id")
async def get_feishu_message(
    message_id: str,
    request: Request = None,
) -> dict[str, Any]:
    require_owner_user(request)

    from deerflow.community.feishu_tools import feishu_get_message_by_id

    result = feishu_get_message_by_id.invoke({"message_id": message_id})
    return {"message": result}


@router.post("/feishu/messages/search", name="search_feishu_messages")
async def search_feishu_messages(
    query: str,
    chat_id: str | None = None,
    page_size: int = 20,
    request: Request = None,
) -> dict[str, Any]:
    require_owner_user(request)

    from deerflow.community.feishu_tools import feishu_search_messages

    result = feishu_search_messages.invoke(
        {
            "query": query,
            "chat_id": chat_id,
            "page_size": page_size,
        }
    )
    return {"results": result}


@router.put("/{channel_type}", response_model=ChannelConfigResponse)
async def update_channel_config(channel_type: str, body: ChannelUpdateRequest, request: Request) -> ChannelConfigResponse:
    require_owner_user(request)

    if channel_type not in SUPPORTED_CHANNEL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid channel type: {channel_type}")

    channels_config = _load_channels_from_yaml()
    if channel_type not in channels_config:
        channels_config[channel_type] = {}

    if body.enabled is not None:
        channels_config[channel_type]["enabled"] = body.enabled
    if body.app_id is not None:
        channels_config[channel_type]["app_id"] = body.app_id
    if body.app_secret is not None:
        channels_config[channel_type]["app_secret"] = body.app_secret
    if body.bot_token is not None:
        channels_config[channel_type]["bot_token"] = body.bot_token
    if body.app_token is not None:
        channels_config[channel_type]["app_token"] = body.app_token
    if body.team_id is not None:
        channels_config[channel_type]["team_id"] = body.team_id
    if body.bot_id is not None:
        channels_config[channel_type]["bot_id"] = body.bot_id
    if body.bot_secret is not None:
        channels_config[channel_type]["bot_secret"] = body.bot_secret
    if body.corp_id is not None:
        channels_config[channel_type]["corp_id"] = body.corp_id
    if body.agent_id is not None:
        channels_config[channel_type]["agent_id"] = body.agent_id
    if body.corp_secret is not None:
        channels_config[channel_type]["corp_secret"] = body.corp_secret
    if body.client_id is not None:
        channels_config[channel_type]["client_id"] = body.client_id
    if body.client_secret is not None:
        channels_config[channel_type]["client_secret"] = body.client_secret

    _save_channels_to_yaml(channels_config)

    logger.info(f"Channel {channel_type} config updated")
    return ChannelConfigResponse(
        feishu=channels_config.get("feishu"),
        slack=channels_config.get("slack"),
        telegram=channels_config.get("telegram"),
        wecom=channels_config.get("wecom"),
        dingtalk=channels_config.get("dingtalk"),
    )


@router.get("/threads", response_model=ChannelThreadsListResponse)
async def list_channel_threads(request: Request) -> ChannelThreadsListResponse:
    require_owner_user(request)
    from app.channels.store import ChannelStore

    store = ChannelStore()
    entries = store.list_entries()
    channels = []
    for entry in entries:
        channels.append(
            ChannelThreadResponse(
                channel=entry.get("channel_name", ""),
                chat_id=entry.get("chat_id", ""),
                topic_id=entry.get("topic_id"),
                thread_id=entry.get("thread_id", ""),
                user_id=entry.get("user_id", ""),
                micx_user_id=entry.get("micx_user_id"),
                micx_workspace_id=entry.get("micx_workspace_id"),
                created_at=entry.get("created_at", 0.0),
                updated_at=entry.get("updated_at", 0.0),
            )
        )
    return ChannelThreadsListResponse(channels=channels)


@router.put("/threads/{thread_id}", response_model=ChannelThreadResponse)
async def update_channel_thread(thread_id: str, body: ChannelThreadUpdateRequest, request: Request) -> ChannelThreadResponse:
    require_owner_user(request)
    from app.channels.store import ChannelStore

    store = ChannelStore()
    entries = store.list_entries()
    updated = False
    result = None
    for entry in entries:
        if entry.get("thread_id") == thread_id:
            success = store.update_thread_mapping(
                channel_name=entry.get("channel_name", ""),
                chat_id=entry.get("chat_id", ""),
                thread_id=thread_id,
                topic_id=entry.get("topic_id"),
                micx_user_id=body.micx_user_id,
                micx_workspace_id=body.micx_workspace_id,
            )
            if success:
                updated = True
                result = ChannelThreadResponse(
                    channel=entry.get("channel_name", ""),
                    chat_id=entry.get("chat_id", ""),
                    topic_id=entry.get("topic_id"),
                    thread_id=thread_id,
                    user_id=entry.get("user_id", ""),
                    micx_user_id=body.micx_user_id if body.micx_user_id is not None else entry.get("micx_user_id"),
                    micx_workspace_id=body.micx_workspace_id if body.micx_workspace_id is not None else entry.get("micx_workspace_id"),
                    created_at=entry.get("created_at", 0.0),
                    updated_at=entry.get("updated_at", 0.0),
                )
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Thread mapping for {thread_id} not found")

    logger.info(f"Channel thread {thread_id} updated: micx_user_id={body.micx_user_id}, micx_workspace_id={body.micx_workspace_id}")
    assert result is not None
    return result


class ChannelConfigUpdate(BaseModel):
    """M3 — per-platform channel configuration to save (tokens / enabled /
    Slack socket-mode), owner-only."""
    feishu: dict[str, Any] | None = None
    slack: dict[str, Any] | None = None
    telegram: dict[str, Any] | None = None
    wecom: dict[str, Any] | None = None
    dingtalk: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class ChannelConfigUpdateResponse(BaseModel):
    success: bool
    message: str


@router.post("/config", response_model=ChannelConfigUpdateResponse)
async def update_channel_config(
    payload: ChannelConfigUpdate, request: Request
) -> ChannelConfigUpdateResponse:
    """Save IM channel configuration (tokens / enabled / slack socket-mode) back
    to config.yaml's ``channels`` section and restart affected channels.

    Only the provided fields are merged; omitted platforms are left unchanged.
    Adding ``slack.mode: socket`` (with an ``app_token``) enables Socket Mode;
    ``mode: webhook`` disables it.
    """
    require_owner_user(request)
    current = _load_channels_from_yaml()
    changed = payload.model_dump(exclude_none=True)
    for name, cfg in changed.items():
        merged = dict(current.get(name) or {})
        if isinstance(cfg, dict):
            for k, v in cfg.items():
                if v is not None:
                    merged[k] = v
        current[name] = merged
    _save_channels_to_yaml(current)

    restarted: list[str] = []
    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is not None:
        for name, cfg in current.items():
            if isinstance(cfg, dict) and cfg.get("enabled"):
                try:
                    if await service.restart_channel(name):
                        restarted.append(name)
                except Exception:  # noqa: BLE001
                    logger.warning("channel %s restart failed", name)
    return ChannelConfigUpdateResponse(
        success=True,
        message=f"channels config saved; restarted={restarted or 'none'}",
    )


@router.put("/{channel_name}", response_model=ChannelConfigUpdateResponse)
async def update_channel_config_entry(
    channel_name: str, payload: dict[str, Any], request: Request
) -> ChannelConfigUpdateResponse:
    """Update a single platform's channel config (enabled / tokens / slack
    socket-mode) in config.yaml and restart it if it becomes enabled.

    Matches the frontend save flow: PUT /api/channels/{id} with the platform's
    editable fields (enabled, app_id, app_secret, bot_token, app_token, ...).
    """
    require_owner_user(request)
    known = {"feishu", "slack", "telegram", "wecom", "dingtalk"}
    if channel_name not in known:
        raise HTTPException(status_code=422, detail=f"unknown channel '{channel_name}'")
    current = _load_channels_from_yaml()
    merged = dict(current.get(channel_name) or {})
    for k, v in payload.items():
        if v is not None:
            merged[k] = v
    current[channel_name] = merged
    _save_channels_to_yaml(current)

    restarted: list[str] = []
    if merged.get("enabled"):
        from app.channels.service import get_channel_service

        service = get_channel_service()
        if service is not None:
            try:
                if await service.restart_channel(channel_name):
                    restarted.append(channel_name)
            except Exception:  # noqa: BLE001
                logger.warning("channel %s restart failed", channel_name)
    return ChannelConfigUpdateResponse(
        success=True,
        message=f"{channel_name} config saved; restarted={','.join(restarted) or 'none'}",
    )
