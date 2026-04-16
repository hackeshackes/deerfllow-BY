import json
import logging
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user, require_user
from deerflow.admin import SkillShare, get_visible_skills_for_user, save_skill_share
from app.gateway.path_utils import resolve_thread_virtual_path
from deerflow.admin import append_admin_audit_record, upsert_skill_metadata
from deerflow.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from deerflow.config.extensions_config import ExtensionsConfig, SkillStateConfig, get_extensions_config, reload_extensions_config
from deerflow.skills import Skill, load_skills
from deerflow.skills.installer import SkillAlreadyExistsError, install_skill_from_archive
from deerflow.skills.manager import (
    append_history,
    atomic_write,
    custom_skill_exists,
    ensure_custom_skill_is_editable,
    get_custom_skill_dir,
    get_custom_skill_file,
    get_skill_history_file,
    public_skill_exists,
    read_custom_skill_content,
    read_history,
    validate_skill_markdown_content,
)
from deerflow.skills.security_scanner import scan_skill_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["skills"])

_GITHUB_REPO_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+))?$")
_GITHUB_ARCHIVE_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/(?:archive|tarball|releases/download)/")


def _resolve_archive_url(url: str) -> tuple[str, str]:
    if _GITHUB_ARCHIVE_RE.match(url):
        url_path = Path(url)
        suffix = url_path.suffix.lower()
        if suffix == ".gz" and str(url_path).endswith(".tar.gz"):
            return url, ".tar.gz"
        if suffix == ".gz":
            return url, ".tar.gz"
        return url, ".zip"

    match = _GITHUB_REPO_RE.match(url)
    if match:
        _user, _repo, branch = match.groups()
        resolved_branch = branch or "main"
        archive_url = f"https://github.com/{_user}/{_repo}/archive/refs/heads/{resolved_branch}.zip"
        return archive_url, ".zip"

    url_path = Path(url)
    url_suffix = url_path.suffix.lower()
    if url_suffix == ".gz" and url_path.stem.endswith(".tar"):
        return url, ".tar.gz"
    if url_suffix in {".skill", ".zip", ".tar.gz"}:
        return url, url_suffix
    return url, ".skill"


class SkillResponse(BaseModel):
    """Response model for skill information."""

    name: str = Field(..., description="Name of the skill")
    description: str = Field(..., description="Description of what the skill does")
    license: str | None = Field(None, description="License information")
    author: str | None = Field(None, description="Author information")
    version: str | None = Field(None, description="Version information")
    compatibility: str | None = Field(None, description="Compatibility information")
    category: str = Field(..., description="Category of the skill (public or custom)")
    enabled: bool = Field(default=True, description="Whether this skill is enabled")
    source: str | None = Field(None, description="Installation source")
    installed_at: str | None = Field(None, description="Install timestamp")
    display_name_zh: str | None = Field(None, description="Chinese display name")
    description_zh: str | None = Field(None, description="Chinese description")


class SkillsListResponse(BaseModel):
    """Response model for listing all skills."""

    skills: list[SkillResponse]


class SkillUpdateRequest(BaseModel):
    """Request model for updating a skill."""

    enabled: bool = Field(..., description="Whether to enable or disable the skill")


class SkillInstallRequest(BaseModel):
    """Request model for installing a skill from a .skill file."""

    thread_id: str = Field(..., description="The thread ID where the .skill file is located")
    path: str = Field(..., description="Virtual path to the .skill file (e.g., mnt/user-data/outputs/my-skill.skill)")


class SkillInstallResponse(BaseModel):
    """Response model for skill installation."""

    success: bool = Field(..., description="Whether the installation was successful")
    skill_name: str = Field(..., description="Name of the installed skill")
    message: str = Field(..., description="Installation result message")
    source: str | None = Field(None, description="Installation source")


class SkillRemoteInstallRequest(BaseModel):
    url: str = Field(..., description="Remote URL to a .skill archive")
    conflict_strategy: str = Field(default="error", description="error, replace, or rename")
    rename_to: str | None = Field(default=None, description="New skill name when conflict_strategy is rename")


class SkillMetadataUpdateRequest(BaseModel):
    display_name_zh: str | None = Field(default=None, description="Chinese display name")
    description_zh: str | None = Field(default=None, description="Chinese description")


class CustomSkillCreateRequest(BaseModel):
    name: str = Field(..., description="Skill name (must be unique)")
    content: str = Field(..., description="SKILL.md content")


class CustomSkillContentResponse(SkillResponse):
    content: str = Field(..., description="Raw SKILL.md content")


class CustomSkillUpdateRequest(BaseModel):
    content: str = Field(..., description="Replacement SKILL.md content")


class CustomSkillHistoryResponse(BaseModel):
    history: list[dict]


class SkillRollbackRequest(BaseModel):
    history_index: int = Field(default=-1, description="History entry index to restore from, defaulting to the latest change.")


class SkillShareRequest(BaseModel):
    visibility: str = Field(..., description="Visibility: 'public' or 'workspace'")
    workspace_id: str | None = Field(None, description="Workspace ID when visibility is 'workspace'")


class SkillRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: str | None = Field(None, description="Optional comment")


class SkillShareResponse(BaseModel):
    skill_name: str
    visibility: str
    workspace_id: str | None = None
    owner_id: str | None = None


class SharedSkillsResponse(BaseModel):
    skills: list[SkillShareResponse]


def _skill_to_response(skill: Skill) -> SkillResponse:
    """Convert a Skill object to a SkillResponse."""
    return SkillResponse(
        name=skill.name,
        description=skill.description,
        license=skill.license,
        author=skill.author,
        version=skill.version,
        compatibility=skill.compatibility,
        category=skill.category,
        enabled=skill.enabled,
        source=skill.source,
        installed_at=skill.installed_at,
        display_name_zh=skill.display_name_zh,
        description_zh=skill.description_zh,
    )


def _extensions_config_path() -> Path:
    config_path = ExtensionsConfig.resolve_config_path()
    if config_path is None:
        return Path.cwd().parent / "extensions_config.json"
    return config_path


def _set_skill_enabled_state(skill_name: str, enabled: bool) -> None:
    config_path = _extensions_config_path()
    current_config = get_extensions_config()
    config_data = {
        "mcpServers": {name: server.model_dump() for name, server in current_config.mcp_servers.items()},
        "skills": {name: {"enabled": skill.enabled} for name, skill in current_config.skills.items()},
    }
    config_data["skills"][skill_name] = {"enabled": enabled}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")
    reload_extensions_config()


def _current_skill(skill_name: str) -> Skill:
    skill = next((item for item in load_skills(enabled_only=False) if item.name == skill_name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found after installation")
    return skill


def _load_custom_skill_response(skill_name: str) -> CustomSkillContentResponse:
    skills = load_skills(enabled_only=False)
    skill = next((s for s in skills if s.name == skill_name and s.category == "custom"), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
    return CustomSkillContentResponse(**_skill_to_response(skill).model_dump(), content=read_custom_skill_content(skill_name))


@router.get(
    "/skills",
    response_model=SkillsListResponse,
    summary="List All Skills",
    description="Retrieve a list of all available skills from both public and custom directories.",
)
async def list_skills(request: Request) -> SkillsListResponse:
    user = require_user(request)
    try:
        visible_skill_names = get_visible_skills_for_user(
            user_id=user.id,
            is_owner=user.is_owner,
            workspace_id=getattr(request.state, "active_workspace_id", None),
        )
        all_skills = load_skills(enabled_only=False)
        visible_skills = [s for s in all_skills if s.name in visible_skill_names]
        return SkillsListResponse(skills=[_skill_to_response(skill) for skill in visible_skills])
    except Exception as e:
        logger.error(f"Failed to load skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load skills: {str(e)}")


@router.post(
    "/skills/install",
    response_model=SkillInstallResponse,
    summary="Install Skill",
    description="Install a skill from a .skill file (ZIP archive) located in the thread's user-data directory.",
)
async def install_skill(request: SkillInstallRequest, http_request: Request) -> SkillInstallResponse:
    user = require_owner_user(http_request)
    try:
        skill_file_path = resolve_thread_virtual_path(request.thread_id, request.path)
        result = install_skill_from_archive(skill_file_path)
        _set_skill_enabled_state(result["skill_name"], True)
        upsert_skill_metadata(result["skill_name"], source=f"thread:{request.thread_id}:{request.path}", installed_at=datetime.now(UTC).isoformat())
        await refresh_skills_system_prompt_cache_async()
        append_admin_audit_record("skill.installed", actor_id=user.id, target=result["skill_name"], details={"source": f"thread:{request.thread_id}:{request.path}"})
        return SkillInstallResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SkillAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install skill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")


@router.post(
    "/skills/install/remote",
    response_model=SkillInstallResponse,
    summary="Install Skill From Remote URL",
)
async def install_skill_from_remote(request: SkillRemoteInstallRequest, http_request: Request) -> SkillInstallResponse:
    user = require_owner_user(http_request)
    try:
        download_url, archive_extension = _resolve_archive_url(request.url)

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / f"remote{archive_extension}"
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                response = await client.get(download_url)
                response.raise_for_status()
            archive_path.write_bytes(response.content)
            result = install_skill_from_archive(
                archive_path,
                conflict_strategy=request.conflict_strategy,
                rename_to=request.rename_to,
            )

        _set_skill_enabled_state(result["skill_name"], False)
        skill = _current_skill(result["skill_name"])
        upsert_skill_metadata(
            result["skill_name"],
            source=request.url,
            installed_at=datetime.now(UTC).isoformat(),
            version=skill.version,
            author=skill.author,
            compatibility=skill.compatibility,
        )

        share = SkillShare(
            skill_name=result["skill_name"],
            owner_id=user.id,
            visibility="private",
        )
        save_skill_share(share)

        await refresh_skills_system_prompt_cache_async()
        append_admin_audit_record(
            "skill.installed_remote",
            actor_id=user.id,
            target=result["skill_name"],
            details={
                "source": request.url,
                "enabled": False,
                "conflict_strategy": request.conflict_strategy,
            },
        )
        return SkillInstallResponse(**result, source=request.url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to download remote skill: {exc}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SkillAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to install remote skill: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to install remote skill: {exc}") from exc


@router.put("/admin/skills/{skill_name}/metadata", response_model=SkillResponse)
async def update_skill_metadata(skill_name: str, body: SkillMetadataUpdateRequest, request: Request) -> SkillResponse:
    user = require_owner_user(request)
    skill = next((item for item in load_skills(enabled_only=False) if item.name == skill_name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    upsert_skill_metadata(
        skill_name,
        display_name_zh=body.display_name_zh,
        description_zh=body.description_zh,
    )
    append_admin_audit_record(
        "skill.metadata_updated",
        actor_id=user.id,
        target=skill_name,
        details={"display_name_zh": bool(body.display_name_zh), "description_zh": bool(body.description_zh)},
    )
    updated_skill = next((item for item in load_skills(enabled_only=False) if item.name == skill_name), None)
    if updated_skill is None:
        raise HTTPException(status_code=500, detail=f"Failed to reload skill '{skill_name}' after metadata update")
    return _skill_to_response(updated_skill)


@router.get("/skills/custom", response_model=SkillsListResponse, summary="List Custom Skills")
async def list_custom_skills(request: Request) -> SkillsListResponse:
    user = require_user(request)
    try:
        all_custom_skills = [skill for skill in load_skills(enabled_only=False) if skill.category == "custom"]
        if user.is_owner:
            return SkillsListResponse(skills=[_skill_to_response(skill) for skill in all_custom_skills])

        visible_skill_names = get_visible_skills_for_user(
            user_id=user.id,
            is_owner=user.is_owner,
            workspace_id=getattr(request.state, "active_workspace_id", None),
        )
        visible_skills = [s for s in all_custom_skills if s.name in visible_skill_names]
        return SkillsListResponse(skills=[_skill_to_response(skill) for skill in visible_skills])
    except Exception as e:
        logger.error("Failed to list custom skills: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list custom skills: {str(e)}")


@router.post("/skills/custom", response_model=CustomSkillContentResponse, status_code=201, summary="Create Custom Skill")
async def create_custom_skill(request: CustomSkillCreateRequest, http_request: Request) -> CustomSkillContentResponse:
    user = require_owner_user(http_request)
    try:
        skill_name = request.name.strip()
        if not skill_name:
            raise HTTPException(status_code=400, detail="Skill name cannot be empty")
        if custom_skill_exists(skill_name):
            raise HTTPException(status_code=409, detail=f"Custom skill '{skill_name}' already exists")
        if public_skill_exists(skill_name):
            raise HTTPException(status_code=409, detail=f"Built-in skill '{skill_name}' exists. Choose a different name.")

        validate_skill_markdown_content(skill_name, request.content)
        scan = await scan_skill_content(request.content, executable=False, location=f"{skill_name}/SKILL.md")
        if scan.decision == "block":
            raise HTTPException(status_code=400, detail=f"Security scan blocked the creation: {scan.reason}")

        skill_dir = get_custom_skill_dir(skill_name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        atomic_write(skill_file, request.content)

        append_history(
            skill_name,
            {
                "action": "human_create",
                "author": "human",
                "thread_id": None,
                "file_path": "SKILL.md",
                "prev_content": None,
                "new_content": request.content,
                "scanner": {"decision": scan.decision, "reason": scan.reason},
            },
        )

        share = SkillShare(
            skill_name=skill_name,
            owner_id=user.id,
            visibility="private",
        )
        save_skill_share(share)

        await refresh_skills_system_prompt_cache_async()
        return _load_custom_skill_response(skill_name)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create custom skill %s: %s", request.name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create custom skill: {str(e)}")


@router.get("/skills/custom/{skill_name}", response_model=CustomSkillContentResponse, summary="Get Custom Skill Content")
async def get_custom_skill(skill_name: str, request: Request) -> CustomSkillContentResponse:
    require_user(request)
    try:
        return _load_custom_skill_response(skill_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get custom skill: {str(e)}")


@router.put("/skills/custom/{skill_name}", response_model=CustomSkillContentResponse, summary="Edit Custom Skill")
async def update_custom_skill(skill_name: str, request: CustomSkillUpdateRequest, http_request: Request) -> CustomSkillContentResponse:
    require_owner_user(http_request)
    try:
        ensure_custom_skill_is_editable(skill_name)
        validate_skill_markdown_content(skill_name, request.content)
        scan = await scan_skill_content(request.content, executable=False, location=f"{skill_name}/SKILL.md")
        if scan.decision == "block":
            raise HTTPException(status_code=400, detail=f"Security scan blocked the edit: {scan.reason}")
        skill_file = get_custom_skill_dir(skill_name) / "SKILL.md"
        prev_content = skill_file.read_text(encoding="utf-8")
        atomic_write(skill_file, request.content)
        append_history(
            skill_name,
            {
                "action": "human_edit",
                "author": "human",
                "thread_id": None,
                "file_path": "SKILL.md",
                "prev_content": prev_content,
                "new_content": request.content,
                "scanner": {"decision": scan.decision, "reason": scan.reason},
            },
        )
        await refresh_skills_system_prompt_cache_async()
        return _load_custom_skill_response(skill_name)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update custom skill: {str(e)}")


@router.delete("/skills/custom/{skill_name}", summary="Delete Custom Skill")
async def delete_custom_skill(skill_name: str, request: Request) -> dict[str, bool]:
    require_owner_user(request)
    try:
        ensure_custom_skill_is_editable(skill_name)
        skill_dir = get_custom_skill_dir(skill_name)
        prev_content = read_custom_skill_content(skill_name)
        append_history(
            skill_name,
            {
                "action": "human_delete",
                "author": "human",
                "thread_id": None,
                "file_path": "SKILL.md",
                "prev_content": prev_content,
                "new_content": None,
                "scanner": {"decision": "allow", "reason": "Deletion requested."},
            },
        )
        shutil.rmtree(skill_dir)
        await refresh_skills_system_prompt_cache_async()
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete custom skill: {str(e)}")


@router.get("/skills/custom/{skill_name}/history", response_model=CustomSkillHistoryResponse, summary="Get Custom Skill History")
async def get_custom_skill_history(skill_name: str, request: Request) -> CustomSkillHistoryResponse:
    require_user(request)
    try:
        if not custom_skill_exists(skill_name) and not get_skill_history_file(skill_name).exists():
            raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
        return CustomSkillHistoryResponse(history=read_history(skill_name))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to read history for %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read history: {str(e)}")


@router.post("/skills/custom/{skill_name}/rollback", response_model=CustomSkillContentResponse, summary="Rollback Custom Skill")
async def rollback_custom_skill(skill_name: str, request: SkillRollbackRequest, http_request: Request) -> CustomSkillContentResponse:
    require_owner_user(http_request)
    try:
        if not custom_skill_exists(skill_name) and not get_skill_history_file(skill_name).exists():
            raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
        history = read_history(skill_name)
        if not history:
            raise HTTPException(status_code=400, detail=f"Custom skill '{skill_name}' has no history")
        record = history[request.history_index]
        target_content = record.get("prev_content")
        if target_content is None:
            raise HTTPException(status_code=400, detail="Selected history entry has no previous content to roll back to")
        validate_skill_markdown_content(skill_name, target_content)
        scan = await scan_skill_content(target_content, executable=False, location=f"{skill_name}/SKILL.md")
        skill_file = get_custom_skill_file(skill_name)
        current_content = skill_file.read_text(encoding="utf-8") if skill_file.exists() else None
        history_entry = {
            "action": "rollback",
            "author": "human",
            "thread_id": None,
            "file_path": "SKILL.md",
            "prev_content": current_content,
            "new_content": target_content,
            "rollback_from_ts": record.get("ts"),
            "scanner": {"decision": scan.decision, "reason": scan.reason},
        }
        if scan.decision == "block":
            append_history(skill_name, history_entry)
            raise HTTPException(status_code=400, detail=f"Rollback blocked by security scanner: {scan.reason}")
        atomic_write(skill_file, target_content)
        append_history(skill_name, history_entry)
        await refresh_skills_system_prompt_cache_async()
        return _load_custom_skill_response(skill_name)
    except HTTPException:
        raise
    except IndexError:
        raise HTTPException(status_code=400, detail="history_index is out of range")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to roll back custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to roll back custom skill: {str(e)}")


@router.get("/skills/shared", response_model=SharedSkillsResponse, summary="List Shared Skills")
async def list_shared_skills(request: Request) -> SharedSkillsResponse:
    user = require_user(request)
    from deerflow.admin import get_shared_skills

    workspace_id = getattr(user, "active_workspace_id", None)
    shares = get_shared_skills(workspace_id=workspace_id)

    return SharedSkillsResponse(
        skills=[
            SkillShareResponse(
                skill_name=s.skill_name,
                visibility=s.visibility,
                workspace_id=s.workspace_id,
                owner_id=s.owner_id,
            )
            for s in shares
        ]
    )


@router.get(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Get Skill Details",
    description="Retrieve detailed information about a specific skill by its name.",
)
async def get_skill(skill_name: str, request: Request) -> SkillResponse:
    require_user(request)
    try:
        skills = load_skills(enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return _skill_to_response(skill)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get skill: {str(e)}")


@router.put(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Update Skill",
    description="Update a skill's enabled status by modifying the extensions_config.json file.",
)
async def update_skill(skill_name: str, request: SkillUpdateRequest, http_request: Request) -> SkillResponse:
    require_owner_user(http_request)
    try:
        skills = load_skills(enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        config_path = ExtensionsConfig.resolve_config_path()
        if config_path is None:
            config_path = Path.cwd().parent / "extensions_config.json"
            logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

        extensions_config = get_extensions_config()
        extensions_config.skills[skill_name] = SkillStateConfig(enabled=request.enabled)

        config_data = {
            "mcpServers": {name: server.model_dump() for name, server in extensions_config.mcp_servers.items()},
            "skills": {name: {"enabled": skill_config.enabled} for name, skill_config in extensions_config.skills.items()},
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Skills configuration updated and saved to: {config_path}")
        reload_extensions_config()
        await refresh_skills_system_prompt_cache_async()

        skills = load_skills(enabled_only=False)
        updated_skill = next((s for s in skills if s.name == skill_name), None)

        if updated_skill is None:
            raise HTTPException(status_code=500, detail=f"Failed to reload skill '{skill_name}' after update")

        logger.info(f"Skill '{skill_name}' enabled status updated to {request.enabled}")
        return _skill_to_response(updated_skill)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {str(e)}")


@router.post("/skills/{skill_name}/share", response_model=SkillShareResponse, summary="Share a Skill")
async def share_skill(skill_name: str, body: SkillShareRequest, request: Request) -> SkillShareResponse:
    user = require_user(request)
    skills = load_skills(enabled_only=False)
    skill = next((s for s in skills if s.name == skill_name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    from deerflow.admin import SkillShare, save_skill_share

    share = SkillShare(
        skill_name=skill_name,
        owner_id=user.id,
        workspace_id=body.workspace_id if body.visibility == "workspace" else None,
        visibility=body.visibility,
    )
    save_skill_share(share)

    append_admin_audit_record(
        "skill.shared",
        actor_id=user.id,
        target=skill_name,
        details={"visibility": body.visibility, "workspace_id": body.workspace_id},
    )

    return SkillShareResponse(
        skill_name=skill_name,
        visibility=share.visibility,
        workspace_id=share.workspace_id,
        owner_id=share.owner_id,
    )


@router.post("/skills/{skill_name}/unshare", response_model=dict)
async def unshare_skill(skill_name: str, request: Request) -> dict:
    user = require_user(request)
    from deerflow.admin import delete_skill_share, get_skill_share

    existing = get_skill_share(skill_name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' is not shared")

    if existing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can unshare the skill")

    delete_skill_share(skill_name)

    append_admin_audit_record(
        "skill.unshared",
        actor_id=user.id,
        target=skill_name,
        details={},
    )

    return {"success": True}


@router.post("/skills/{skill_name}/rate", response_model=dict)
async def rate_skill(skill_name: str, body: SkillRatingRequest, request: Request) -> dict:
    user = require_user(request)
    skills = load_skills(enabled_only=False)
    skill = next((s for s in skills if s.name == skill_name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    from deerflow.admin import SkillRating, add_skill_rating

    rating = SkillRating(
        skill_name=skill_name,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    add_skill_rating(rating)

    return {"success": True, "message": "Rating submitted successfully"}
