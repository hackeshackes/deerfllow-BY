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
    """Get channel configuration from config.yaml."""
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


@router.put("/{channel_type}", response_model=ChannelConfigResponse)
async def update_channel_config(
    channel_type: str, body: ChannelUpdateRequest, request: Request
) -> ChannelConfigResponse:
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
