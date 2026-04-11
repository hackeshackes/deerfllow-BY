from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user, require_user
from deerflow.config import get_app_config
from deerflow.config.app_config import reload_app_config
from deerflow.config.model_config import ModelConfig
from deerflow.config.paths import get_paths
from deerflow.models.factory import create_chat_model

router = APIRouter(prefix="/api", tags=["models"])


class ModelResponse(BaseModel):
    name: str = Field(..., description="Unique identifier for the model")
    model: str = Field(..., description="Actual provider model identifier")
    display_name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="Model description")
    use: str | None = Field(None, description="Provider implementation path")
    base_url: str | None = Field(None, description="Provider base URL")
    api_key: str | None = Field(None, description="API key value or env placeholder")
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


def _override_path() -> Path:
    return get_paths().models_override_file


def _read_override_data() -> dict[str, Any]:
    path = _override_path()
    if not path.exists():
        return {"models": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("models", [])
    return data


def _write_override_data(data: dict[str, Any]) -> None:
    path = _override_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _model_to_response(model: ModelConfig, *, is_default: bool = False) -> ModelResponse:
    return ModelResponse(
        name=model.name,
        model=model.model,
        display_name=model.display_name,
        description=model.description,
        use=model.use,
        base_url=getattr(model, "base_url", None),
        api_key=getattr(model, "api_key", None),
        temperature=getattr(model, "temperature", None),
        supports_thinking=model.supports_thinking,
        supports_reasoning_effort=model.supports_reasoning_effort,
        supports_vision=model.supports_vision,
        enabled=bool(getattr(model, "enabled", True)),
        is_default=is_default,
    )


def _normalize_model_record(payload: ModelMutationRequest) -> dict[str, Any]:
    record = payload.model_dump(exclude_none=True)
    if payload.is_default:
        record["is_default"] = True
    return record


@router.get("/models", response_model=ModelsListResponse)
async def list_models(request: Request) -> ModelsListResponse:
    require_user(request)
    config = get_app_config()
    default_name = config.models[0].name if config.models else None
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name) for model in config.models if bool(getattr(model, "enabled", True))])


@router.get("/models/{model_name}", response_model=ModelResponse)
async def get_model(model_name: str, request: Request) -> ModelResponse:
    require_user(request)
    config = get_app_config()
    model = config.get_model_config(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    default_name = config.models[0].name if config.models else None
    return _model_to_response(model, is_default=model.name == default_name)


@router.get("/admin/models", response_model=ModelsListResponse)
async def list_admin_models(request: Request) -> ModelsListResponse:
    require_owner_user(request)
    config = get_app_config()
    default_name = config.models[0].name if config.models else None
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name) for model in config.models])


@router.post("/admin/models", response_model=ModelResponse, status_code=201)
async def create_admin_model(payload: ModelMutationRequest, request: Request) -> ModelResponse:
    require_owner_user(request)
    data = _read_override_data()
    if any(item.get("name") == payload.name for item in data["models"]):
        raise HTTPException(status_code=409, detail="模型名称已存在")
    if payload.is_default:
        for item in data["models"]:
            item["is_default"] = False
    data["models"].append(_normalize_model_record(payload))
    _write_override_data(data)
    config = reload_app_config()
    model = config.get_model_config(payload.name)
    return _model_to_response(model, is_default=payload.is_default)


@router.patch("/admin/models/{model_name}", response_model=ModelResponse)
async def update_admin_model(model_name: str, payload: ModelMutationRequest, request: Request) -> ModelResponse:
    require_owner_user(request)
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
    _write_override_data(data)
    config = reload_app_config()
    model = config.get_model_config(payload.name)
    return _model_to_response(model, is_default=payload.is_default)


@router.post("/admin/models/{model_name}/reload", response_model=ModelsListResponse)
async def reload_admin_models(model_name: str, request: Request) -> ModelsListResponse:
    require_owner_user(request)
    config = reload_app_config()
    default_name = config.models[0].name if config.models else None
    return ModelsListResponse(models=[_model_to_response(model, is_default=model.name == default_name) for model in config.models])


@router.post("/admin/models/{model_name}/test", response_model=ModelTestResponse)
async def test_admin_model(model_name: str, request: Request) -> ModelTestResponse:
    require_owner_user(request)
    try:
        model = create_chat_model(model_name)
        response = await model.ainvoke("只回复：测试成功")
        content = getattr(response, "content", None)
        return ModelTestResponse(ok=True, message=str(content)[:200] if content else "连接成功")
    except Exception as exc:  # noqa: BLE001
        return ModelTestResponse(ok=False, message=str(exc))
