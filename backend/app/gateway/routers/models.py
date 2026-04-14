from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user, require_user
from deerflow.admin import append_admin_audit_record, is_secret_ref, upsert_secret
from deerflow.config import get_app_config
from deerflow.config.app_config import AppConfig, reload_app_config
from deerflow.config.model_config import ModelConfig
from deerflow.config.paths import get_paths

router = APIRouter(prefix="/api", tags=["models"])


class ModelResponse(BaseModel):
    name: str = Field(..., description="Unique identifier for the model")
    model: str = Field(..., description="Actual provider model identifier")
    display_name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="Model description")
    use: str | None = Field(None, description="Provider implementation path")
    base_url: str | None = Field(None, description="Provider base URL")
    api_key: str | None = Field(None, description="API key value or env placeholder")
    api_key_configured: bool = Field(default=False, description="Whether an API key or secret reference is configured")
    temperature: float | None = Field(None, description="Sampling temperature")
    supports_thinking: bool = Field(default=False)
    supports_reasoning_effort: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    enabled: bool = Field(default=True)
    is_default: bool = Field(default=False)


class ModelsListResponse(BaseModel):
    models: list[ModelResponse]


class ModelMutationRequest(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    use: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    supports_thinking: bool = False
    supports_reasoning_effort: bool = False
    supports_vision: bool = False
    enabled: bool = True
    is_default: bool = False


class ModelTestResponse(BaseModel):
    ok: bool
    message: str


class ModelDeleteResponse(BaseModel):
    success: bool
    message: str


def _override_path() -> Path:
    return get_paths().models_override_file


def _read_override_data() -> dict[str, Any]:
    path = _override_path()
    if not path.exists():
        return {"models": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("models", [])
    return data


def _read_base_models() -> list[dict[str, Any]]:
    config_path = AppConfig.resolve_config_path()
    if not config_path.exists():
        return []
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    models = data.get("models") or []
    return [item for item in models if isinstance(item, dict)]


def _write_override_data(data: dict[str, Any]) -> None:
    path = _override_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _persist_and_reload(data: dict[str, Any]):
    previous = _read_override_data()
    _write_override_data(data)
    try:
        return reload_app_config()
    except Exception as exc:  # noqa: BLE001
        _write_override_data(previous)
        reload_app_config()
        raise HTTPException(status_code=422, detail=f"模型配置无效：{exc}") from exc


def _model_to_response(model: ModelConfig, *, is_default: bool = False, include_sensitive: bool = False) -> ModelResponse:
    api_key = getattr(model, "api_key", None)
    return ModelResponse(
        name=model.name,
        model=model.model,
        display_name=model.display_name,
        description=model.description,
        use=model.use if include_sensitive else None,
        base_url=getattr(model, "base_url", None) if include_sensitive else None,
        api_key=api_key if include_sensitive else None,
        api_key_configured=bool(api_key),
        temperature=getattr(model, "temperature", None),
        supports_thinking=model.supports_thinking,
        supports_reasoning_effort=model.supports_reasoning_effort,
        supports_vision=model.supports_vision,
        enabled=bool(getattr(model, "enabled", True)),
        is_default=is_default,
    )


def _normalize_model_record(payload: ModelMutationRequest) -> dict[str, Any]:
    record = payload.model_dump(exclude_none=True)
    api_key = record.get("api_key")
    if isinstance(api_key, str) and api_key and not api_key.startswith("$") and not is_secret_ref(api_key):
        record["api_key"] = upsert_secret(f"models/{payload.name}/api_key", api_key)
    if payload.is_default:
        record["is_default"] = True
    record.pop("deleted", None)
    return record


def _default_model_name(config) -> str | None:
    return config.get_default_model_name()


@router.get("/models", response_model=ModelsListResponse)
async def list_models(request: Request) -> ModelsListResponse:
    require_user(request)
    config = get_app_config()
    default_name = _default_model_name(config)
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name, include_sensitive=False) for model in config.models if bool(getattr(model, "enabled", True))])


@router.get("/models/{model_name}", response_model=ModelResponse)
async def get_model(model_name: str, request: Request) -> ModelResponse:
    require_user(request)
    config = get_app_config()
    model = config.get_model_config(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    default_name = _default_model_name(config)
    return _model_to_response(model, is_default=model.name == default_name, include_sensitive=False)


@router.get("/admin/models", response_model=ModelsListResponse)
async def list_admin_models(request: Request) -> ModelsListResponse:
    require_owner_user(request)
    config = get_app_config()
    default_name = _default_model_name(config)
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name, include_sensitive=True) for model in config.models])


@router.post("/admin/models", response_model=ModelResponse, status_code=201)
async def create_admin_model(payload: ModelMutationRequest, request: Request) -> ModelResponse:
    user = require_owner_user(request)
    data = _read_override_data()
    if any(item.get("name") == payload.name for item in data["models"]):
        raise HTTPException(status_code=409, detail="模型名称已存在")
    if payload.is_default:
        for item in data["models"]:
            item["is_default"] = False
    data["models"].append(_normalize_model_record(payload))
    config = _persist_and_reload(data)
    model = config.get_model_config(payload.name)
    append_admin_audit_record("model.created", actor_id=user.id, target=payload.name, details={"is_default": payload.is_default})
    return _model_to_response(model, is_default=payload.is_default, include_sensitive=True)


@router.patch("/admin/models/{model_name}", response_model=ModelResponse)
async def update_admin_model(model_name: str, payload: ModelMutationRequest, request: Request) -> ModelResponse:
    user = require_owner_user(request)
    data = _read_override_data()
    updated = False
    for item in data["models"]:
        if item.get("name") != model_name:
            continue
        item.update(_normalize_model_record(payload))
        item["name"] = payload.name
        updated = True
    if not updated:
        data["models"].append(_normalize_model_record(payload))
    if payload.is_default:
        for item in data["models"]:
            if item.get("name") != payload.name:
                item["is_default"] = False
    config = _persist_and_reload(data)
    model = config.get_model_config(payload.name)
    append_admin_audit_record("model.updated", actor_id=user.id, target=payload.name, details={"original_name": model_name, "is_default": payload.is_default})
    return _model_to_response(model, is_default=payload.is_default, include_sensitive=True)


@router.post("/admin/models/{model_name}/reload", response_model=ModelsListResponse)
async def reload_admin_models(model_name: str, request: Request) -> ModelsListResponse:
    require_owner_user(request)
    config = reload_app_config()
    default_name = _default_model_name(config)
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name, include_sensitive=True) for model in config.models])


@router.post("/admin/models/{model_name}/test", response_model=ModelTestResponse)
async def test_admin_model(model_name: str, request: Request) -> ModelTestResponse:
    require_owner_user(request)
    try:
        from deerflow.models.factory import create_chat_model

        model = create_chat_model(model_name)
        response = await model.ainvoke("只回复：测试成功")
        content = getattr(response, "content", None)
        return ModelTestResponse(ok=True, message=str(content)[:200] if content else "连接成功")
    except Exception as exc:  # noqa: BLE001
        return ModelTestResponse(ok=False, message=str(exc))


@router.delete("/admin/models/{model_name}", response_model=ModelDeleteResponse)
async def delete_admin_model(model_name: str, request: Request) -> ModelDeleteResponse:
    user = require_owner_user(request)
    data = _read_override_data()
    base_model_names = {item.get("name") for item in _read_base_models() if item.get("name")}
    existing_override = next((item for item in data["models"] if item.get("name") == model_name), None)

    if model_name in base_model_names:
        remaining = [item for item in data["models"] if item.get("name") != model_name]
        remaining.append({"name": model_name, "deleted": True})
        data["models"] = remaining
    else:
        remaining = [item for item in data["models"] if item.get("name") != model_name]
        if existing_override is None and len(remaining) == len(data["models"]):
            raise HTTPException(status_code=404, detail="模型不存在")
        data["models"] = remaining

    _persist_and_reload(data)
    append_admin_audit_record("model.deleted", actor_id=user.id, target=model_name)
    return ModelDeleteResponse(success=True, message=f"模型 {model_name} 已删除")
