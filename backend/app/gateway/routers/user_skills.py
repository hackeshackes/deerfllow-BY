from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.gateway.auth import require_user
from deerflow.admin import (
    UserSkillConfig,
    get_skill_average_rating,
    get_skill_ratings,
    get_user_skill_config,
    get_visible_skills_for_user,
    save_user_skill_config,
)
from deerflow.skills import load_skills

router = APIRouter(prefix="/api/user/skills", tags=["user-skills"])


class UserSkillConfigResponse(BaseModel):
    skill_name: str
    display_name: str
    description: str
    enabled: bool
    is_default: bool
    config: dict[str, str]
    average_rating: float | None


class UserSkillConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    is_default: bool | None = None
    config: dict[str, str] | None = None


class UserSkillConfigListResponse(BaseModel):
    skills: list[UserSkillConfigResponse]


def _get_skill_info(skill_name: str) -> tuple[str, str]:
    skills = load_skills()
    for skill in skills:
        if skill.name == skill_name:
            name = skill.display_name_zh or skill.name
            desc = skill.description_zh or skill.description
            return name, desc
    return skill_name, ""


@router.get("", response_model=UserSkillConfigListResponse)
async def list_user_skills(request: Request) -> UserSkillConfigListResponse:
    user = require_user(request)
    store = get_user_skill_config()
    user_configs = {c.skill_name: c for c in store.get_user_configs(user.id)}

    workspace_id = getattr(request.state, "active_workspace_id", None)
    visible_skill_names = get_visible_skills_for_user(
        user_id=user.id,
        is_owner=user.is_owner,
        workspace_id=workspace_id,
    )

    all_skills = load_skills()

    result: list[UserSkillConfigResponse] = []
    for skill_name, config in user_configs.items():
        if skill_name not in visible_skill_names:
            continue
        display_name, description = _get_skill_info(skill_name)
        result.append(
            UserSkillConfigResponse(
                skill_name=skill_name,
                display_name=display_name,
                description=description,
                enabled=config.enabled,
                is_default=config.is_default,
                config=config.config,
                average_rating=get_skill_average_rating(skill_name),
            )
        )

    for skill in all_skills:
        if skill.name not in user_configs and skill.name in visible_skill_names:
            display_name = skill.display_name_zh or skill.name
            description = skill.description_zh or skill.description
            result.append(
                UserSkillConfigResponse(
                    skill_name=skill.name,
                    display_name=display_name,
                    description=description,
                    enabled=skill.enabled,
                    is_default=False,
                    config={},
                    average_rating=get_skill_average_rating(skill.name),
                )
            )

    return UserSkillConfigListResponse(skills=result)


@router.put("/{skill_name}/config", response_model=UserSkillConfigResponse)
async def update_skill_config(
    skill_name: str, body: UserSkillConfigUpdateRequest, request: Request
) -> UserSkillConfigResponse:
    user = require_user(request)
    store = get_user_skill_config()

    config = store.get_user_config(user.id, skill_name)
    if not config:
        config = UserSkillConfig(skill_name=skill_name, user_id=user.id)

    if body.enabled is not None:
        config.enabled = body.enabled
    if body.is_default is not None:
        if body.is_default:
            for c in store.configs:
                if c.user_id == user.id:
                    c.is_default = False
        config.is_default = body.is_default
    if body.config is not None:
        config.config = body.config

    store.upsert(config)
    save_user_skill_config(store)

    display_name, description = _get_skill_info(skill_name)
    return UserSkillConfigResponse(
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        enabled=config.enabled,
        is_default=config.is_default,
        config=config.config,
        average_rating=get_skill_average_rating(skill_name),
    )


@router.post("/{skill_name}/enable", response_model=UserSkillConfigResponse)
async def enable_skill(skill_name: str, request: Request) -> UserSkillConfigResponse:
    user = require_user(request)
    store = get_user_skill_config()

    config = store.get_user_config(user.id, skill_name)
    if not config:
        config = UserSkillConfig(skill_name=skill_name, user_id=user.id)
    config.enabled = True
    config.updated_at = datetime.now(UTC)

    store.upsert(config)
    save_user_skill_config(store)

    display_name, description = _get_skill_info(skill_name)
    return UserSkillConfigResponse(
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        enabled=config.enabled,
        is_default=config.is_default,
        config=config.config,
        average_rating=get_skill_average_rating(skill_name),
    )


@router.post("/{skill_name}/disable", response_model=UserSkillConfigResponse)
async def disable_skill(skill_name: str, request: Request) -> UserSkillConfigResponse:
    user = require_user(request)
    store = get_user_skill_config()

    config = store.get_user_config(user.id, skill_name)
    if not config:
        config = UserSkillConfig(skill_name=skill_name, user_id=user.id)
    config.enabled = False
    config.updated_at = datetime.now(UTC)

    store.upsert(config)
    save_user_skill_config(store)

    display_name, description = _get_skill_info(skill_name)
    return UserSkillConfigResponse(
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        enabled=config.enabled,
        is_default=config.is_default,
        config=config.config,
        average_rating=get_skill_average_rating(skill_name),
    )


@router.get("/{skill_name}/ratings", response_model=list[dict])
async def get_skill_reviews(skill_name: str, request: Request) -> list[dict]:
    ratings = get_skill_ratings(skill_name)
    return [
        {
            "user_id": r.user_id,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat(),
        }
        for r in ratings
    ]