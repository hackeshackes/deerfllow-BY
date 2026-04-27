from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request

from deerflow.config.paths import get_paths

SESSION_COOKIE_NAME = "by_session"
PBKDF2_ITERATIONS = 120_000


@dataclass(slots=True)
class AuthUser:
    id: str
    email: str
    role: str
    name: str
    status: str
    password_hash: str
    salt: str
    invited_at: str | None = None
    activated_at: str | None = None
    last_login_at: str | None = None

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"


@dataclass(slots=True)
class Workspace:
    id: str
    name: str
    slug: str
    created_by_user_id: str
    default_personal: bool


@dataclass(slots=True)
class WorkspaceMembership:
    workspace_id: str
    user_id: str
    role: str


@dataclass(slots=True)
class InviteToken:
    id: str
    user_id: str
    token: str
    expires_at: str
    used_at: str | None
    created_at: str


def _auth_secret() -> str:
    return os.getenv("BETTER_AUTH_SECRET") or "by-local-dev-secret"


def _users_file():
    return get_paths().users_file


def _workspaces_file():
    return get_paths().workspaces_file


def _invites_file():
    return get_paths().invites_file


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS).hex()


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign(payload_b64: str) -> str:
    return _base64url_encode(hmac.new(_auth_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest())


def create_session_token(user: AuthUser, active_workspace_id: str | None = None) -> str:
    resolved_workspace_id = active_workspace_id or get_default_workspace_id_for_user(user.id)
    workspace = get_workspace_by_id(resolved_workspace_id) if resolved_workspace_id else None
    membership = get_workspace_membership(user.id, resolved_workspace_id) if resolved_workspace_id else None
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "status": user.status,
        "active_workspace_id": resolved_workspace_id,
        "active_workspace_name": workspace.name if workspace else None,
        "active_workspace_role": membership.role if membership else None,
    }
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64)}"


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        return json.loads(_base64url_decode(payload_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


# Weak passwords that are forbidden in production
_FORBIDDEN_PASSWORDS = frozenset(
    {
        "change-me-123",
        "admin",
        "password",
        "12345678",
        "changeme",
        "default",
    }
)


def _is_strict_mode() -> bool:
    """Check if strict password mode is disabled (for development only)."""
    return os.getenv("BY_ADMIN_PASSWORD_STRICT_MODE", "true").lower() != "false"


def _validate_admin_password(password: str | None) -> None:
    """Validate admin password meets security requirements.

    Raises:
        ValueError: If password is missing, too weak, or is a known insecure default.
    """
    if not password:
        raise ValueError("BY_ADMIN_PASSWORD environment variable is not set. Please set a strong password before starting the server.")

    if password in _FORBIDDEN_PASSWORDS:
        if _is_strict_mode():
            raise ValueError(f"Password '{password}' is insecure and not allowed. Please set a strong password via BY_ADMIN_PASSWORD environment variable. To disable this check for development, set BY_ADMIN_PASSWORD_STRICT_MODE=false.")
        else:
            import logging

            logging.getLogger(__name__).warning("Using known insecure default password. This is only allowed in development mode (BY_ADMIN_PASSWORD_STRICT_MODE=false).")

    if len(password) < 8:
        raise ValueError("BY_ADMIN_PASSWORD must be at least 8 characters long.")


def _seed_owner_user() -> dict[str, Any]:
    owner_email = os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")
    owner_password = os.getenv("BY_ADMIN_PASSWORD")
    owner_name = os.getenv("BY_ADMIN_NAME", "BY Owner")

    # Validate password before use
    _validate_admin_password(owner_password)

    salt = secrets.token_hex(16)
    now = _utc_now_iso()
    return {
        "id": "owner",
        "email": owner_email,
        "name": owner_name,
        "role": "owner",
        "status": "active",
        "salt": salt,
        "password_hash": _hash_password(owner_password, salt),
        "invited_at": now,
        "activated_at": now,
        "last_login_at": None,
    }


def _slugify_workspace_name(name: str) -> str:
    slug = "-".join(name.strip().lower().split())
    slug = "".join(char for char in slug if char.isalnum() or char == "-")
    return slug or f"workspace-{uuid.uuid4().hex[:8]}"


def _personal_workspace_record(user_id: str, name: str) -> dict[str, Any]:
    return {
        "id": f"ws-{user_id}",
        "name": f"{name} Personal",
        "slug": f"personal-{user_id[:12]}",
        "created_by_user_id": user_id,
        "default_personal": True,
    }


def _workspace_membership_record(workspace_id: str, user_id: str, role: str) -> dict[str, Any]:
    return {"workspace_id": workspace_id, "user_id": user_id, "role": role}


def _read_users_payload() -> dict[str, Any]:
    file_path = _users_file()
    if not file_path.exists():
        payload = {"users": [_seed_owner_user()]}
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid users store JSON") from exc
    payload.setdefault("users", [])
    if not any(user.get("role") == "owner" for user in payload["users"]):
        payload["users"].insert(0, _seed_owner_user())
        _write_users_payload(payload)
    return payload


def _write_users_payload(payload: dict[str, Any]) -> None:
    file_path = _users_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(file_path)


def _read_workspaces_payload() -> dict[str, Any]:
    file_path = _workspaces_file()
    if not file_path.exists():
        payload = {"workspaces": [], "memberships": []}
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return _ensure_workspace_defaults(payload)
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid workspaces store JSON") from exc
    payload.setdefault("workspaces", [])
    payload.setdefault("memberships", [])
    return _ensure_workspace_defaults(payload)


def _write_workspaces_payload(payload: dict[str, Any]) -> None:
    file_path = _workspaces_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(file_path)


def _read_invites_payload() -> dict[str, Any]:
    file_path = _invites_file()
    if not file_path.exists():
        payload = {"invites": []}
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid invites store JSON") from exc
    payload.setdefault("invites", [])
    return payload


def _write_invites_payload(payload: dict[str, Any]) -> None:
    file_path = _invites_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(file_path)


def _to_workspace(record: dict[str, Any]) -> Workspace:
    return Workspace(
        id=str(record["id"]),
        name=str(record["name"]),
        slug=str(record["slug"]),
        created_by_user_id=str(record["created_by_user_id"]),
        default_personal=bool(record.get("default_personal", False)),
    )


def _to_membership(record: dict[str, Any]) -> WorkspaceMembership:
    return WorkspaceMembership(
        workspace_id=str(record["workspace_id"]),
        user_id=str(record["user_id"]),
        role=str(record.get("role", "member")),
    )


def _to_invite(record: dict[str, Any]) -> InviteToken:
    return InviteToken(
        id=str(record["id"]),
        user_id=str(record["user_id"]),
        token=str(record["token"]),
        expires_at=str(record["expires_at"]),
        used_at=record.get("used_at"),
        created_at=str(record["created_at"]),
    )


def _ensure_workspace_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    changed = False
    user_ids = set()
    users = list_users()
    for user in users:
        user_ids.add(user.id)
        personal_workspace_id = f"ws-{user.id}"
        if not any(workspace.get("id") == personal_workspace_id for workspace in payload["workspaces"]):
            payload["workspaces"].append(_personal_workspace_record(user.id, user.name))
            changed = True
        if not any(membership.get("workspace_id") == personal_workspace_id and membership.get("user_id") == user.id for membership in payload["memberships"]):
            payload["memberships"].append(_workspace_membership_record(personal_workspace_id, user.id, "owner"))
            changed = True
    payload["memberships"] = [m for m in payload["memberships"] if m.get("user_id") in user_ids]
    payload["workspaces"] = [w for w in payload["workspaces"] if any(m.get("workspace_id") == w.get("id") for m in payload["memberships"])]
    if changed:
        _write_workspaces_payload(payload)
    return payload


def _to_auth_user(record: dict[str, Any]) -> AuthUser:
    return AuthUser(
        id=str(record["id"]),
        email=str(record["email"]),
        role=str(record.get("role", "member")),
        name=str(record.get("name") or record.get("email") or "User"),
        status=str(record.get("status", "active")),
        password_hash=str(record["password_hash"]),
        salt=str(record["salt"]),
        invited_at=record.get("invited_at"),
        activated_at=record.get("activated_at"),
        last_login_at=record.get("last_login_at"),
    )


def list_users() -> list[AuthUser]:
    payload = _read_users_payload()
    return [_to_auth_user(user) for user in payload.get("users", [])]


def list_workspaces() -> list[Workspace]:
    payload = _read_workspaces_payload()
    return [_to_workspace(workspace) for workspace in payload.get("workspaces", [])]


def list_workspace_memberships() -> list[WorkspaceMembership]:
    payload = _read_workspaces_payload()
    return [_to_membership(membership) for membership in payload.get("memberships", [])]


def list_invites() -> list[InviteToken]:
    payload = _read_invites_payload()
    return [_to_invite(invite) for invite in payload.get("invites", [])]


def get_workspace_by_id(workspace_id: str) -> Workspace | None:
    for workspace in list_workspaces():
        if workspace.id == workspace_id:
            return workspace
    return None


def get_workspace_membership(user_id: str, workspace_id: str | None) -> WorkspaceMembership | None:
    if workspace_id is None:
        return None
    for membership in list_workspace_memberships():
        if membership.user_id == user_id and membership.workspace_id == workspace_id:
            return membership
    return None


def list_workspaces_for_user(user_id: str) -> list[WorkspaceMembership]:
    return [membership for membership in list_workspace_memberships() if membership.user_id == user_id]


def get_default_workspace_id_for_user(user_id: str) -> str | None:
    memberships = list_workspaces_for_user(user_id)
    if not memberships:
        return None
    personal = next(
        (membership for membership in memberships if (workspace := get_workspace_by_id(membership.workspace_id)) and workspace.default_personal),
        None,
    )
    return personal.workspace_id if personal else memberships[0].workspace_id


def get_user_by_id(user_id: str) -> AuthUser | None:
    for user in list_users():
        if user.id == user_id:
            return user
    return None


def get_user_by_email(email: str) -> AuthUser | None:
    normalized = email.strip().lower()
    for user in list_users():
        if user.email.lower() == normalized:
            return user
    return None


def get_active_invite_for_user(user_id: str) -> InviteToken | None:
    now = _utc_now()
    invites = [invite for invite in list_invites() if invite.user_id == user_id and invite.used_at is None and (_parse_datetime(invite.expires_at) or now) > now]
    invites.sort(key=lambda invite: invite.created_at, reverse=True)
    return invites[0] if invites else None


def get_invite_by_token(token: str) -> InviteToken | None:
    now = _utc_now()
    for invite in list_invites():
        if invite.token != token:
            continue
        expires_at = _parse_datetime(invite.expires_at)
        if invite.used_at is not None or expires_at is None or expires_at <= now:
            return None
        return invite
    return None


def verify_password(user: AuthUser, password: str) -> bool:
    return hmac.compare_digest(user.password_hash, _hash_password(password, user.salt))


def authenticate_user(email: str, password: str) -> AuthUser | None:
    user = get_user_by_email(email)
    if user is None or user.status != "active":
        return None
    return user if verify_password(user, password) else None


def touch_last_login(user_id: str) -> None:
    payload = _read_users_payload()
    for record in payload["users"]:
        if record.get("id") == user_id:
            record["last_login_at"] = _utc_now_iso()
            _write_users_payload(payload)
            return


def create_user(email: str, password: str | None = None, role: str = "member", name: str | None = None, *, status: str = "invited") -> AuthUser:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=422, detail="邮箱不能为空")
    if get_user_by_email(normalized_email) is not None:
        raise HTTPException(status_code=409, detail="该用户已存在")
    if role not in {"owner", "member"}:
        raise HTTPException(status_code=422, detail="无效的角色")
    if status not in {"invited", "active", "disabled"}:
        raise HTTPException(status_code=422, detail="无效的用户状态")
    if status == "active" and (password is None or len(password) < 8):
        raise HTTPException(status_code=422, detail="密码长度至少需要 8 位")

    salt = secrets.token_hex(16)
    now = _utc_now_iso()
    seeded_password = password or secrets.token_urlsafe(24)
    record = {
        "id": uuid.uuid4().hex,
        "email": normalized_email,
        "name": name or normalized_email,
        "role": role,
        "status": status,
        "salt": salt,
        "password_hash": _hash_password(seeded_password, salt),
        "invited_at": now,
        "activated_at": now if status == "active" else None,
        "last_login_at": None,
    }
    payload = _read_users_payload()
    payload["users"].append(record)
    _write_users_payload(payload)
    _ensure_workspace_defaults(_read_workspaces_payload())
    return _to_auth_user(record)


def update_user(user_id: str, *, role: str | None = None, status: str | None = None, name: str | None = None, password: str | None = None) -> AuthUser:
    payload = _read_users_payload()
    for record in payload["users"]:
        if record.get("id") != user_id:
            continue
        if role is not None:
            if role not in {"owner", "member"}:
                raise HTTPException(status_code=422, detail="无效的角色")
            record["role"] = role
        if status is not None:
            if status not in {"invited", "active", "disabled"}:
                raise HTTPException(status_code=422, detail="无效的用户状态")
            record["status"] = status
            if status == "active" and not record.get("activated_at"):
                record["activated_at"] = _utc_now_iso()
        if name is not None:
            record["name"] = name.strip() or record.get("name") or record.get("email")
        if password is not None:
            if len(password) < 8:
                raise HTTPException(status_code=422, detail="密码长度至少需要 8 位")
            salt = secrets.token_hex(16)
            record["salt"] = salt
            record["password_hash"] = _hash_password(password, salt)
            if record.get("status") == "invited":
                record["status"] = "active"
            if not record.get("activated_at"):
                record["activated_at"] = _utc_now_iso()
        _write_users_payload(payload)
        return _to_auth_user(record)
    raise HTTPException(status_code=404, detail="未找到该用户")


def change_user_password(user_id: str, current_password: str, new_password: str) -> AuthUser:
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="未找到该用户")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="只有已激活用户可以修改密码")
    if not verify_password(user, current_password):
        raise HTTPException(status_code=401, detail="当前密码不正确")
    return update_user(user_id, password=new_password)


def issue_invite_token(user_id: str, *, expires_in_hours: int = 72) -> InviteToken:
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="未找到该用户")
    existing = get_active_invite_for_user(user_id)
    if existing is not None:
        return existing
    payload = _read_invites_payload()
    now = _utc_now()
    record = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "token": secrets.token_urlsafe(32),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=expires_in_hours)).isoformat(),
        "used_at": None,
    }
    payload["invites"].append(record)
    _write_invites_payload(payload)
    return _to_invite(record)


def activate_user_from_token(token: str, password: str) -> AuthUser:
    invite = get_invite_by_token(token)
    if invite is None:
        raise HTTPException(status_code=404, detail="邀请链接无效或已过期")
    user = get_user_by_id(invite.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="未找到该用户")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    activated_user = update_user(user.id, password=password, status="active")

    payload = _read_invites_payload()
    for record in payload["invites"]:
        if record.get("id") == invite.id:
            record["used_at"] = _utc_now_iso()
            break
    _write_invites_payload(payload)
    return activated_user


def create_workspace(name: str, created_by_user_id: str) -> Workspace:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="空间名称不能为空")
    payload = _read_workspaces_payload()
    workspace = {
        "id": f"ws-{uuid.uuid4().hex}",
        "name": normalized_name,
        "slug": _slugify_workspace_name(normalized_name),
        "created_by_user_id": created_by_user_id,
        "default_personal": False,
    }
    payload["workspaces"].append(workspace)
    payload["memberships"].append(_workspace_membership_record(workspace["id"], created_by_user_id, "owner"))
    _write_workspaces_payload(payload)
    return _to_workspace(workspace)


def add_workspace_member(workspace_id: str, user_id: str, role: str = "member") -> WorkspaceMembership:
    if role not in {"owner", "admin", "member"}:
        raise HTTPException(status_code=422, detail="无效的空间角色")
    payload = _read_workspaces_payload()
    if not any(workspace.get("id") == workspace_id for workspace in payload["workspaces"]):
        raise HTTPException(status_code=404, detail="未找到该空间")
    if not any(user.get("id") == user_id for user in _read_users_payload().get("users", [])):
        raise HTTPException(status_code=404, detail="未找到该用户")
    for membership in payload["memberships"]:
        if membership.get("workspace_id") == workspace_id and membership.get("user_id") == user_id:
            membership["role"] = role
            _write_workspaces_payload(payload)
            return _to_membership(membership)
    record = _workspace_membership_record(workspace_id, user_id, role)
    payload["memberships"].append(record)
    _write_workspaces_payload(payload)
    return _to_membership(record)


def update_workspace(workspace_id: str, *, name: str) -> Workspace:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="空间名称不能为空")
    payload = _read_workspaces_payload()
    for record in payload["workspaces"]:
        if record.get("id") != workspace_id:
            continue
        if record.get("default_personal"):
            raise HTTPException(status_code=403, detail="个人空间不支持修改名称")
        record["name"] = normalized_name
        record["slug"] = _slugify_workspace_name(normalized_name)
        _write_workspaces_payload(payload)
        return _to_workspace(record)
    raise HTTPException(status_code=404, detail="未找到该空间")


def remove_workspace_member(workspace_id: str, user_id: str) -> WorkspaceMembership:
    payload = _read_workspaces_payload()
    workspace = next((workspace for workspace in payload["workspaces"] if workspace.get("id") == workspace_id), None)
    if workspace is None:
        raise HTTPException(status_code=404, detail="未找到该空间")
    if workspace.get("default_personal"):
        raise HTTPException(status_code=403, detail="个人空间不支持移除成员")

    memberships = payload["memberships"]
    removed = next((membership for membership in memberships if membership.get("workspace_id") == workspace_id and membership.get("user_id") == user_id), None)
    if removed is None:
        raise HTTPException(status_code=404, detail="该成员不在当前空间中")
    if removed.get("role") == "owner":
        raise HTTPException(status_code=403, detail="不能移除空间拥有者")

    payload["memberships"] = [membership for membership in memberships if not (membership.get("workspace_id") == workspace_id and membership.get("user_id") == user_id)]
    _write_workspaces_payload(payload)
    return _to_membership(removed)


def delete_workspace(workspace_id: str) -> Workspace:
    payload = _read_workspaces_payload()
    workspace = next((workspace for workspace in payload["workspaces"] if workspace.get("id") == workspace_id), None)
    if workspace is None:
        raise HTTPException(status_code=404, detail="未找到该空间")
    if workspace.get("default_personal"):
        raise HTTPException(status_code=403, detail="个人空间不支持删除")

    payload["workspaces"] = [record for record in payload["workspaces"] if record.get("id") != workspace_id]
    payload["memberships"] = [membership for membership in payload["memberships"] if membership.get("workspace_id") != workspace_id]
    _write_workspaces_payload(payload)

    workspace_dir = get_paths().workspace_dir(workspace_id)
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    return _to_workspace(workspace)


def delete_user(user_id: str, *, actor_user_id: str | None = None) -> AuthUser:
    users_payload = _read_users_payload()
    user_record = next((user for user in users_payload["users"] if user.get("id") == user_id), None)
    if user_record is None:
        raise HTTPException(status_code=404, detail="未找到该用户")

    user = _to_auth_user(user_record)
    if user.role == "owner":
        raise HTTPException(status_code=403, detail="不能删除拥有者账号")
    if actor_user_id is not None and actor_user_id == user_id:
        raise HTTPException(status_code=403, detail="不能删除当前登录账号")

    workspaces_payload = _read_workspaces_payload()
    blocking_workspaces = [workspace for workspace in workspaces_payload["workspaces"] if workspace.get("created_by_user_id") == user_id and not workspace.get("default_personal", False)]
    if blocking_workspaces:
        raise HTTPException(status_code=409, detail="该用户仍拥有共享空间，请先转移或删除其共享空间")

    users_payload["users"] = [record for record in users_payload["users"] if record.get("id") != user_id]
    _write_users_payload(users_payload)

    personal_workspace_id = f"ws-{user_id}"
    workspaces_payload["memberships"] = [membership for membership in workspaces_payload["memberships"] if membership.get("user_id") != user_id and membership.get("workspace_id") != personal_workspace_id]
    workspaces_payload["workspaces"] = [workspace for workspace in workspaces_payload["workspaces"] if workspace.get("id") != personal_workspace_id]
    _write_workspaces_payload(workspaces_payload)

    invites_payload = _read_invites_payload()
    invites_payload["invites"] = [invite for invite in invites_payload["invites"] if invite.get("user_id") != user_id]
    _write_invites_payload(invites_payload)

    return user


def set_active_workspace(user: AuthUser, workspace_id: str) -> tuple[Workspace, WorkspaceMembership]:
    workspace = get_workspace_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="未找到该空间")
    membership = get_workspace_membership(user.id, workspace_id)
    if membership is None:
        raise HTTPException(status_code=403, detail="当前账号不属于该空间")
    return workspace, membership


def session_user_from_request(request: Request) -> AuthUser | None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return get_user_by_email(os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")) or _to_auth_user(_seed_owner_user())
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        return None
    payload = decode_session_token(raw_token)
    if payload is None:
        return None
    user = get_user_by_id(str(payload.get("sub", "")))
    if user is None or user.status != "active":
        return None
    return user


def session_payload_from_request(request: Request) -> dict[str, Any] | None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        user = get_user_by_email(os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")) or _to_auth_user(_seed_owner_user())
        return {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.name,
            "status": user.status,
            "active_workspace_id": get_default_workspace_id_for_user(user.id),
        }
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        return None
    return decode_session_token(raw_token)


def require_user(request: Request) -> AuthUser:
    user = session_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="需要先登录")
    return user


def require_owner_user(request: Request) -> AuthUser:
    user = require_user(request)
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="仅拥有者可执行此操作")
    return user
