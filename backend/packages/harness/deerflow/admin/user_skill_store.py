from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from pydantic import BaseModel, Field

from deerflow.config.paths import get_paths

_user_skill_config_lock = Lock()
_cached_user_skill_config: UserSkillConfigStore | None = None
_cached_skill_shares: dict[str, SkillShare] | None = None
_cached_skill_ratings: dict[str, list[SkillRating]] | None = None
_shares_lock = Lock()
_ratings_lock = Lock()


class UserSkillConfig(BaseModel):
    """Per-user skill configuration."""

    skill_name: str
    user_id: str
    enabled: bool = True
    config: dict[str, str] = Field(default_factory=dict)
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillShare(BaseModel):
    """Skill sharing configuration."""

    skill_name: str
    owner_id: str
    workspace_id: str | None = None  # None = globally shared
    visibility: str = "private"  # "private" | "workspace" | "public"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillRating(BaseModel):
    """Skill rating and review."""

    skill_name: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserSkillConfigStore(BaseModel):
    """Store for all user skill configurations."""

    configs: list[UserSkillConfig] = Field(default_factory=list)

    def get_user_config(self, user_id: str, skill_name: str) -> UserSkillConfig | None:
        return next(
            (c for c in self.configs if c.user_id == user_id and c.skill_name == skill_name),
            None,
        )

    def get_user_configs(self, user_id: str) -> list[UserSkillConfig]:
        return [c for c in self.configs if c.user_id == user_id]

    def upsert(self, config: UserSkillConfig) -> None:
        existing = self.get_user_config(config.user_id, config.skill_name)
        if existing:
            self.configs.remove(existing)
        config.updated_at = datetime.now(UTC)
        self.configs.append(config)


def _user_skill_config_path() -> Path:
    return get_paths().admin_dir / "user_skill_config.json"


def _skill_shares_path() -> Path:
    return get_paths().admin_dir / "skill_shares.json"


def _skill_ratings_path() -> Path:
    return get_paths().admin_dir / "skill_ratings.json"


def _read_user_skill_config() -> UserSkillConfigStore:
    path = _user_skill_config_path()
    if not path.exists():
        return UserSkillConfigStore()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UserSkillConfigStore.model_validate(payload)


def _read_skill_shares() -> dict[str, SkillShare]:
    path = _skill_shares_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: SkillShare.model_validate(v) for k, v in data.items()}


def _read_skill_ratings() -> dict[str, list[SkillRating]]:
    path = _skill_ratings_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: [SkillRating.model_validate(r) for r in v] for k, v in data.items()}


def get_user_skill_config() -> UserSkillConfigStore:
    global _cached_user_skill_config
    if _cached_user_skill_config is None:
        with _user_skill_config_lock:
            if _cached_user_skill_config is None:
                _cached_user_skill_config = _read_user_skill_config()
    return _cached_user_skill_config


def save_user_skill_config(store: UserSkillConfigStore) -> UserSkillConfigStore:
    global _cached_user_skill_config
    path = _user_skill_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(store.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    with _user_skill_config_lock:
        _cached_user_skill_config = store
    return store


def get_skill_share(skill_name: str) -> SkillShare | None:
    shares = _get_skill_shares()
    return shares.get(skill_name)


def _get_skill_shares() -> dict[str, SkillShare]:
    global _cached_skill_shares
    if _cached_skill_shares is None:
        with _shares_lock:
            if _cached_skill_shares is None:
                _cached_skill_shares = _read_skill_shares()
    return _cached_skill_shares


def save_skill_share(share: SkillShare) -> SkillShare:
    global _cached_skill_shares
    shares = _get_skill_shares()
    shares[share.skill_name] = share
    path = _skill_shares_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps({k: v.model_dump(mode="json") for k, v in shares.items()}, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    with _shares_lock:
        _cached_skill_shares = shares
    return share


def delete_skill_share(skill_name: str) -> bool:
    global _cached_skill_shares
    shares = _get_skill_shares()
    if skill_name not in shares:
        return False
    del shares[skill_name]
    path = _skill_shares_path()
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps({k: v.model_dump(mode="json") for k, v in shares.items()}, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    with _shares_lock:
        _cached_skill_shares = shares
    return True


def get_shared_skills(workspace_id: str | None = None) -> list[SkillShare]:
    shares = _get_skill_shares()
    result = []
    for share in shares.values():
        if share.visibility == "public":
            result.append(share)
        elif share.visibility == "workspace" and share.workspace_id == workspace_id:
            result.append(share)
    return result


def add_skill_rating(rating: SkillRating) -> SkillRating:
    global _cached_skill_ratings
    if _cached_skill_ratings is None:
        with _ratings_lock:
            if _cached_skill_ratings is None:
                _cached_skill_ratings = _read_skill_ratings()
    ratings = _cached_skill_ratings
    if rating.skill_name not in ratings:
        ratings[rating.skill_name] = []
    # Check if user already rated
    existing = next((r for r in ratings[rating.skill_name] if r.user_id == rating.user_id), None)
    if existing:
        ratings[rating.skill_name].remove(existing)
    ratings[rating.skill_name].append(rating)
    path = _skill_ratings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps({k: [r.model_dump(mode="json") for r in v] for k, v in ratings.items()}, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    with _ratings_lock:
        _cached_skill_ratings = ratings
    return rating


def get_skill_ratings(skill_name: str) -> list[SkillRating]:
    ratings = _get_skill_ratings()
    return ratings.get(skill_name, [])


def _get_skill_ratings() -> dict[str, list[SkillRating]]:
    global _cached_skill_ratings
    if _cached_skill_ratings is None:
        with _ratings_lock:
            if _cached_skill_ratings is None:
                _cached_skill_ratings = _read_skill_ratings()
    return _cached_skill_ratings


def get_skill_average_rating(skill_name: str) -> float | None:
    ratings = get_skill_ratings(skill_name)
    if not ratings:
        return None
    return sum(r.rating for r in ratings) / len(ratings)


def user_is_in_workspace(user_id: str, workspace_id: str | None) -> bool:
    """Check if user is a member of the given workspace."""
    if workspace_id is None:
        return False
    from deerflow.admin.user_store import list_workspace_memberships

    for membership in list_workspace_memberships():
        if membership.user_id == user_id and membership.workspace_id == workspace_id:
            return True
    return False


def get_visible_skills_for_user(user_id: str, is_owner: bool, workspace_id: str | None = None) -> list[str]:
    """Get list of skill names visible to a user based on ownership and visibility rules.

    Rules:
    - Admin (is_owner=True): sees ALL skills
    - Regular user: sees skills where:
      1. skill.owner_id == user_id (own skill)
      2. skill.visibility == "public" (admin shared publicly)
      3. skill.visibility == "workspace" AND user is in that workspace
    Note: Skills without share records are NOT visible to regular users (treated as private).
    """
    if is_owner:
        # Admin sees all skills
        from deerflow.skills import load_skills

        return [s.name for s in load_skills(enabled_only=False)]

    shares = _get_skill_shares()
    visible_skill_names: list[str] = []

    from deerflow.skills import load_skills

    all_skills = load_skills(enabled_only=False)
    for skill in all_skills:
        share = shares.get(skill.name)
        if share is None:
            # No share record = private skill, not visible to regular users
            continue
        if share.owner_id == user_id:
            # Own skill
            visible_skill_names.append(skill.name)
        elif share.visibility == "public":
            # Admin shared publicly
            visible_skill_names.append(skill.name)
        elif share.visibility == "workspace" and user_is_in_workspace(user_id, share.workspace_id):
            # User is in the same workspace
            visible_skill_names.append(skill.name)

    return visible_skill_names
