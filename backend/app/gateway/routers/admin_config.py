from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user
from deerflow.admin import append_admin_audit_record, get_admin_config, read_admin_audit_records, save_admin_config
from deerflow.config import reset_tracing_config
from deerflow.config.app_config import reload_app_config

router = APIRouter(prefix="/api/admin", tags=["admin-config"])


class AdminTracingProviderResponse(BaseModel):
    enabled: bool = False
    api_key: str | None = None
    public_key: str | None = None
    secret_key: str | None = None
    project: str | None = None
    endpoint: str | None = None
    host: str | None = None


class AdminTracingResponse(BaseModel):
    langsmith: AdminTracingProviderResponse
    langfuse: AdminTracingProviderResponse


class AdminBrandingResponse(BaseModel):
    name: str
    short_name: str
    tagline: str
    description: str
    support_email: str
    website_path: str
    docs_path: str


class AdminSystemResponse(BaseModel):
    log_level: str | None = None
    token_usage_enabled: bool | None = None


class AdminConfigResponse(BaseModel):
    system: AdminSystemResponse
    tracing: AdminTracingResponse
    branding: AdminBrandingResponse


class AdminConfigUpdateRequest(AdminConfigResponse):
    pass


class AdminAuditListResponse(BaseModel):
    records: list[dict] = Field(default_factory=list)


def _to_response() -> AdminConfigResponse:
    return AdminConfigResponse.model_validate(get_admin_config().masked().model_dump())


@router.get("/public/branding", response_model=AdminBrandingResponse)
async def get_public_branding() -> AdminBrandingResponse:
    return AdminBrandingResponse.model_validate(get_admin_config().branding.model_dump())


@router.get("/config", response_model=AdminConfigResponse)
async def get_admin_configuration(request: Request) -> AdminConfigResponse:
    require_owner_user(request)
    return _to_response()


@router.put("/config", response_model=AdminConfigResponse)
async def update_admin_configuration(body: AdminConfigUpdateRequest, request: Request) -> AdminConfigResponse:
    user = require_owner_user(request)
    save_admin_config(body)
    reset_tracing_config()
    reload_app_config()
    append_admin_audit_record(
        "admin_config.updated",
        actor_id=user.id,
        target="admin/config",
        details={
            "sections": ["system", "tracing", "branding"],
        },
    )
    return _to_response()


@router.get("/audit", response_model=AdminAuditListResponse)
async def get_admin_audit(request: Request) -> AdminAuditListResponse:
    require_owner_user(request)
    return AdminAuditListResponse(records=read_admin_audit_records())
