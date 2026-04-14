from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.gateway.auth import list_users, list_workspaces, require_owner_user
from deerflow.admin import get_admin_config, read_admin_audit_records
from deerflow.config import get_app_config, get_enabled_tracing_providers, get_explicitly_enabled_tracing_providers, get_paths, get_tracing_config
from deerflow.skills import load_skills

router = APIRouter(prefix="/api/admin/monitoring", tags=["admin-monitoring"])


class MonitoringHealthResponse(BaseModel):
    gateway: str
    runtime_initialized: bool
    checkpointer_initialized: bool
    store_initialized: bool
    tracing_enabled_providers: list[str] = Field(default_factory=list)
    tracing_explicit_providers: list[str] = Field(default_factory=list)


class MonitoringMetricsResponse(BaseModel):
    user_count: int = 0
    workspace_count: int = 0
    model_count: int = 0
    skill_count: int = 0
    custom_skill_count: int = 0
    thread_count: int = 0
    upload_file_count: int = 0
    artifact_file_count: int = 0
    agent_count: int = 0
    run_count: int = 0
    token_usage_enabled: bool = False


class MonitoringOverviewResponse(BaseModel):
    health: MonitoringHealthResponse
    metrics: MonitoringMetricsResponse
    tracing: dict = Field(default_factory=dict)
    branding: dict = Field(default_factory=dict)
    recent_audit: list[dict] = Field(default_factory=list)


def _count_directories(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.iterdir() if item.is_dir())


def _count_files_under(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _collect_filesystem_metrics() -> MonitoringMetricsResponse:
    paths = get_paths()
    app_config = get_app_config()
    skills = load_skills(enabled_only=False)
    metrics = MonitoringMetricsResponse(
        user_count=len(list_users()),
        workspace_count=len(list_workspaces()),
        model_count=len(app_config.models),
        skill_count=len(skills),
        custom_skill_count=len([skill for skill in skills if skill.category == "custom"]),
        token_usage_enabled=bool(app_config.token_usage.enabled),
    )

    thread_roots = [paths.base_dir / "threads"]
    if paths.users_dir.exists():
        thread_roots.extend(user_dir / "threads" for user_dir in paths.users_dir.iterdir() if user_dir.is_dir())
    if paths.workspaces_dir.exists():
        thread_roots.extend(workspace_dir / "threads" for workspace_dir in paths.workspaces_dir.iterdir() if workspace_dir.is_dir())

    thread_ids: set[Path] = set()
    upload_count = 0
    artifact_count = 0
    for root in thread_roots:
        if not root.exists():
            continue
        for thread_dir in root.iterdir():
            if not thread_dir.is_dir():
                continue
            thread_ids.add(thread_dir.resolve())
            upload_count += _count_files_under(thread_dir / "user-data" / "uploads")
            artifact_count += _count_files_under(thread_dir / "user-data" / "outputs")

    metrics.thread_count = len(thread_ids)
    metrics.upload_file_count = upload_count
    metrics.artifact_file_count = artifact_count
    metrics.agent_count = _count_directories(paths.agents_dir)
    return metrics


@router.get("/overview", response_model=MonitoringOverviewResponse)
async def get_monitoring_overview(request: Request) -> MonitoringOverviewResponse:
    require_owner_user(request)
    tracing_config = get_tracing_config()
    metrics = _collect_filesystem_metrics()

    run_manager = getattr(request.app.state, "run_manager", None)
    if run_manager is not None:
        metrics.run_count = len(getattr(run_manager, "_runs", {}))

    admin_config = get_admin_config().masked()
    return MonitoringOverviewResponse(
        health=MonitoringHealthResponse(
            gateway="healthy",
            runtime_initialized=bool(getattr(request.app.state, "stream_bridge", None) and getattr(request.app.state, "run_manager", None)),
            checkpointer_initialized=bool(getattr(request.app.state, "checkpointer", None)),
            store_initialized=bool(getattr(request.app.state, "store", None)),
            tracing_enabled_providers=get_enabled_tracing_providers(),
            tracing_explicit_providers=get_explicitly_enabled_tracing_providers(),
        ),
        metrics=metrics,
        tracing={
            "langsmith": {
                "enabled": tracing_config.langsmith.enabled,
                "configured": tracing_config.langsmith.is_configured,
                "project": tracing_config.langsmith.project,
                "endpoint": tracing_config.langsmith.endpoint,
            },
            "langfuse": {
                "enabled": tracing_config.langfuse.enabled,
                "configured": tracing_config.langfuse.is_configured,
                "host": tracing_config.langfuse.host,
            },
        },
        branding=admin_config.branding.model_dump(),
        recent_audit=read_admin_audit_records(limit=20),
    )
