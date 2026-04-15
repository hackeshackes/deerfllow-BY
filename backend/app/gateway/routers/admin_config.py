from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user
from deerflow.admin import append_admin_audit_record, get_admin_config, read_admin_audit_records, save_admin_config
from deerflow.admin.config_store import (
    AdminBrandingConfig,
    AdminMCPServerConfig,
    AdminModelConfig,
    AdminSandboxConfig,
    AdminSkillConfig,
    AdminSystemConfig,
    AdminToolConfig,
    AdminTracingConfig,
    AdminUploadConfig,
)
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


class AdminUploadResponse(BaseModel):
    max_size_mb: int = 10
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".jpg", ".png"])
    convert_to_markdown: bool = True


class AdminSandboxResponse(BaseModel):
    use: str = "deerflow.sandbox.local:LocalSandboxProvider"
    allow_host_bash: bool = False
    bash_output_max_chars: int = 20000
    read_file_output_max_chars: int = 50000
    ls_output_max_chars: int = 20000


class AdminModelResponse(BaseModel):
    name: str
    display_name: str
    use: str
    model: str
    api_key: str | None = None
    api_base: str | None = None
    request_timeout: float = 600.0
    max_retries: int = 2
    max_tokens: int = 4096
    temperature: float = 0.7
    supports_vision: bool = False
    supports_thinking: bool = False
    is_default: bool = False


class AdminToolResponse(BaseModel):
    name: str
    group: str
    use: str
    enabled: bool = True


class AdminSkillResponse(BaseModel):
    auto_update: bool = False
    security_scan: bool = True


class AdminMCPServerResponse(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class AdminConfigResponse(BaseModel):
    system: AdminSystemResponse
    tracing: AdminTracingResponse
    branding: AdminBrandingResponse
    upload: AdminUploadResponse
    sandbox: AdminSandboxResponse
    models: list[AdminModelResponse] = Field(default_factory=list)
    tools: list[AdminToolResponse] = Field(default_factory=list)
    skills: AdminSkillResponse
    mcp: list[AdminMCPServerResponse] = Field(default_factory=list)


class AdminConfigUpdateRequest(BaseModel):
    system: AdminSystemConfig | None = None
    tracing: AdminTracingConfig | None = None
    branding: AdminBrandingConfig | None = None
    upload: AdminUploadConfig | None = None
    sandbox: AdminSandboxConfig | None = None
    models: list[AdminModelConfig] | None = None
    tools: list[AdminToolConfig] | None = None
    skills: AdminSkillConfig | None = None
    mcp: list[AdminMCPServerConfig] | None = None


class AdminAuditListResponse(BaseModel):
    records: list[dict] = Field(default_factory=list)


def _to_response() -> AdminConfigResponse:
    config = get_admin_config().masked()
    return AdminConfigResponse(
        system=AdminSystemResponse(**config.system.model_dump()),
        tracing=AdminTracingResponse(
            langsmith=AdminTracingProviderResponse(**config.tracing.langsmith.model_dump()),
            langfuse=AdminTracingProviderResponse(**config.tracing.langfuse.model_dump()),
        ),
        branding=AdminBrandingResponse(**config.branding.model_dump()),
        upload=AdminUploadResponse(**config.upload.model_dump()),
        sandbox=AdminSandboxResponse(**config.sandbox.model_dump()),
        models=[AdminModelResponse(**m.model_dump()) for m in config.models],
        tools=[AdminToolResponse(**t.model_dump()) for t in config.tools],
        skills=AdminSkillResponse(**config.skills.model_dump()),
        mcp=[AdminMCPServerResponse(**m.model_dump()) for m in config.mcp],
    )


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

    current_config = get_admin_config()

    update_data = body.model_dump(exclude_unset=True, exclude_none=True)
    for section, value in update_data.items():
        setattr(current_config, section, value)

    save_admin_config(current_config)
    reset_tracing_config()
    reload_app_config()
    append_admin_audit_record(
        "admin_config.updated",
        actor_id=user.id,
        target="admin/config",
        details={
            "sections": list(update_data.keys()),
        },
    )
    return _to_response()


@router.get("/config/schema", response_model=dict)
async def get_config_schema(request: Request) -> dict:
    require_owner_user(request)
    return {
        "system": AdminSystemResponse.model_json_schema(),
        "tracing": AdminTracingResponse.model_json_schema(),
        "branding": AdminBrandingResponse.model_json_schema(),
        "upload": AdminUploadResponse.model_json_schema(),
        "sandbox": AdminSandboxResponse.model_json_schema(),
        "models": AdminModelResponse.model_json_schema(),
        "tools": AdminToolResponse.model_json_schema(),
        "skills": AdminSkillResponse.model_json_schema(),
        "mcp": AdminMCPServerResponse.model_json_schema(),
    }


@router.post("/config/validate", response_model=dict)
async def validate_config(body: AdminConfigUpdateRequest, request: Request) -> dict:
    require_owner_user(request)
    errors = []

    if body.models is not None:
        for i, model in enumerate(body.models):
            if not model.name:
                errors.append({"section": "models", "index": i, "field": "name", "message": "Model name is required"})
            if not model.use:
                errors.append({"section": "models", "index": i, "field": "use", "message": "Model provider is required"})

    if body.mcp is not None:
        for i, mcp_server in enumerate(body.mcp):
            if not mcp_server.name:
                errors.append({"section": "mcp", "index": i, "field": "name", "message": "MCP server name is required"})
            if not mcp_server.command:
                errors.append({"section": "mcp", "index": i, "field": "command", "message": "MCP server command is required"})

    if errors:
        raise HTTPException(status_code=400, detail={"message": "Validation failed", "errors": errors})

    return {"valid": True, "message": "Configuration is valid"}


@router.get("/audit", response_model=AdminAuditListResponse)
async def get_admin_audit(request: Request) -> AdminAuditListResponse:
    require_owner_user(request)
    return AdminAuditListResponse(records=read_admin_audit_records())
