"""Custom Skills CRUD API - User-managed skill creation and sharing."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.auth_context import get_current_workspace_id
from deerflow.skills.manager import (
    atomic_write,
    custom_skill_exists,
    get_custom_skill_dir,
    get_custom_skill_file,
    list_custom_skills,
    read_custom_skill_content,
    validate_skill_markdown_content,
    validate_skill_name,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user/skills/custom", tags=["custom-skills"])


class CustomSkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=200)
    description: str = ""
    content: str = Field(min_length=1)


class CustomSkillUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    content: str | None = None


class CustomSkillResponse(BaseModel):
    name: str
    display_name: str
    description: str
    content: str
    author_id: str
    workspace_id: str | None = None
    visibility: str = "private"
    created_at: str
    updated_at: str


_custom_skills_meta: dict[str, dict] = {}


def _get_skill_meta(name: str) -> dict | None:
    for meta in _custom_skills_meta.values():
        if meta["name"] == name:
            return meta
    return None


def _build_skill_response(name: str, author_id: str, workspace_id: str | None) -> CustomSkillResponse:
    meta = _get_skill_meta(name)
    content = read_custom_skill_content(name)

    frontmatter_match = content.split("---")
    display_name = name
    description = ""
    if len(frontmatter_match) >= 2:
        for line in frontmatter_match[1].split("\n"):
            if line.startswith("display_name:"):
                display_name = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')

    return CustomSkillResponse(
        name=name,
        display_name=meta.get("display_name", display_name) if meta else display_name,
        description=meta.get("description", description) if meta else description,
        content=content,
        author_id=author_id,
        workspace_id=workspace_id,
        visibility=meta.get("visibility", "private") if meta else "private",
        created_at=meta.get("created_at", str(time.time())) if meta else str(time.time()),
        updated_at=meta.get("updated_at", str(time.time())) if meta else str(time.time()),
    )


@router.get("", response_model=list[CustomSkillResponse])
async def list_custom_skills_handler(request: Request) -> list[CustomSkillResponse]:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    skills = []
    for skill in list_custom_skills():
        meta = _get_skill_meta(skill.name)
        if meta and meta["author_id"] != user.id:
            continue
        skills.append(_build_skill_response(skill.name, user.id, workspace_id))
    return skills


@router.post("", response_model=CustomSkillResponse)
async def create_custom_skill(body: CustomSkillCreateRequest, request: Request) -> CustomSkillResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    try:
        normalized_name = validate_skill_name(body.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if custom_skill_exists(normalized_name):
        raise HTTPException(status_code=409, detail=f"Skill '{normalized_name}' already exists")

    content = body.content
    if not content.startswith("---"):
        content = f"""---
name: {normalized_name}
display_name: {body.display_name}
description: {body.description}
---

{content}
"""

    try:
        validate_skill_markdown_content(normalized_name, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    skill_file = get_custom_skill_file(normalized_name)
    atomic_write(skill_file, content)

    now = time.time()
    meta = {
        "id": str(uuid.uuid4()),
        "name": normalized_name,
        "display_name": body.display_name,
        "description": body.description,
        "author_id": user.id,
        "workspace_id": workspace_id,
        "visibility": "private",
        "created_at": now,
        "updated_at": now,
    }
    _custom_skills_meta[meta["id"]] = meta

    logger.info(f"Custom skill created: {normalized_name} by user {user.id}")
    return _build_skill_response(normalized_name, user.id, workspace_id)


@router.get("/{skill_name}", response_model=CustomSkillResponse)
async def get_custom_skill(skill_name: str, request: Request) -> CustomSkillResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    try:
        normalized_name = validate_skill_name(skill_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not custom_skill_exists(normalized_name):
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    meta = _get_skill_meta(normalized_name)
    if meta and meta["author_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    return _build_skill_response(normalized_name, user.id, workspace_id)


@router.put("/{skill_name}", response_model=CustomSkillResponse)
async def update_custom_skill(
    skill_name: str, body: CustomSkillUpdateRequest, request: Request
) -> CustomSkillResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    try:
        normalized_name = validate_skill_name(skill_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not custom_skill_exists(normalized_name):
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    meta = _get_skill_meta(normalized_name)
    if not meta or meta["author_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the author can edit this skill")

    content = read_custom_skill_content(normalized_name)

    if body.content is not None:
        try:
            validate_skill_markdown_content(normalized_name, body.content)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        content = body.content

    if body.display_name is not None or body.description is not None:
        frontmatter_match = content.split("---")
        if len(frontmatter_match) >= 2:
            frontmatter_lines = frontmatter_match[1].split("\n")
            new_frontmatter = []
            for line in frontmatter_lines:
                if body.display_name is not None and line.startswith("display_name:"):
                    new_frontmatter.append(f'display_name: "{body.display_name}"')
                elif body.description is not None and line.startswith("description:"):
                    new_frontmatter.append(f'description: "{body.description}"')
                else:
                    new_frontmatter.append(line)
            content = "---".join([frontmatter_match[0]] + ["\n".join(new_frontmatter)] + frontmatter_match[2:])

    skill_file = get_custom_skill_file(normalized_name)
    atomic_write(skill_file, content)

    now = time.time()
    meta["updated_at"] = now
    if body.display_name is not None:
        meta["display_name"] = body.display_name
    if body.description is not None:
        meta["description"] = body.description

    logger.info(f"Custom skill updated: {normalized_name} by user {user.id}")
    return _build_skill_response(normalized_name, user.id, workspace_id)


@router.delete("/{skill_name}")
async def delete_custom_skill(skill_name: str, request: Request) -> dict:
    user = require_user(request)

    try:
        normalized_name = validate_skill_name(skill_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not custom_skill_exists(normalized_name):
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    meta = _get_skill_meta(normalized_name)
    if not meta or meta["author_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the author can delete this skill")

    skill_dir = get_custom_skill_dir(normalized_name)
    import shutil
    shutil.rmtree(skill_dir)

    for meta_id, m in list(_custom_skills_meta.items()):
        if m["name"] == normalized_name:
            del _custom_skills_meta[meta_id]

    logger.info(f"Custom skill deleted: {normalized_name} by user {user.id}")
    return {"success": True, "message": f"Skill '{normalized_name}' deleted"}


class SkillShareRequest(BaseModel):
    target_workspace_id: str
    permission: str = "read"


class SkillShareResponse(BaseModel):
    id: str
    skill_name: str
    target_workspace_id: str
    permission: str
    shared_by: str
    shared_at: str


_skill_shares: dict[str, dict] = {}


@router.post("/{skill_name}/share", response_model=SkillShareResponse)
async def share_custom_skill(
    skill_name: str, body: SkillShareRequest, request: Request
) -> SkillShareResponse:
    user = require_user(request)

    try:
        normalized_name = validate_skill_name(skill_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not custom_skill_exists(normalized_name):
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    meta = _get_skill_meta(normalized_name)
    if not meta or meta["author_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the author can share this skill")

    for existing_share in _skill_shares.values():
        if existing_share["skill_name"] == normalized_name and existing_share["target_workspace_id"] == body.target_workspace_id:
            raise HTTPException(status_code=409, detail="Already shared to this workspace")

    share_id = str(uuid.uuid4())
    now = time.time()
    share = {
        "id": share_id,
        "skill_name": normalized_name,
        "target_workspace_id": body.target_workspace_id,
        "permission": body.permission,
        "shared_by": user.id,
        "shared_at": now,
    }
    _skill_shares[share_id] = share
    logger.info(f"Skill {normalized_name} shared to workspace {body.target_workspace_id}")

    return SkillShareResponse(
        id=share["id"],
        skill_name=share["skill_name"],
        target_workspace_id=share["target_workspace_id"],
        permission=share["permission"],
        shared_by=share["shared_by"],
        shared_at=str(share["shared_at"]),
    )


@router.delete("/{skill_name}/share/{share_id}")
async def unshare_custom_skill(skill_name: str, share_id: str, request: Request) -> dict:
    user = require_user(request)

    try:
        normalized_name = validate_skill_name(skill_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not custom_skill_exists(normalized_name):
        raise HTTPException(status_code=404, detail=f"Skill '{normalized_name}' not found")

    meta = _get_skill_meta(normalized_name)
    if not meta or meta["author_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the author can unshare this skill")

    share = _skill_shares.get(share_id)
    if not share or share["skill_name"] != normalized_name:
        raise HTTPException(status_code=404, detail=f"Share {share_id} not found")

    del _skill_shares[share_id]
    logger.info(f"Skill {normalized_name} unshared (share {share_id})")
    return {"success": True, "message": f"Share {share_id} removed"}
