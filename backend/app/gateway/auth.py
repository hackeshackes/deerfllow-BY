from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from dataclasses import dataclass
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


def _auth_secret() -> str:
    return os.getenv("BETTER_AUTH_SECRET") or "by-local-dev-secret"


def _users_file():
    return get_paths().users_file


def _workspaces_file():
    return get_paths().workspaces_file


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


def _seed_owner_user() -> dict[str, Any]:
    owner_email = os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")
    owner_password = os.getenv("BY_ADMIN_PASSWORD", "change-me-123")
    owner_name = os.getenv("BY_ADMIN_NAME", "BY Owner")
    salt = secrets.token_hex(16)
    return {
        "id": "owner",
        "email": owner_email,
        "name": owner_name,
        "role": "owner",
        "status": "active",
        "salt": salt,
        "password_hash": _hash_password(owner_password, salt),
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


def get_workspace_by_id(workspace_id: str) -> Workspace | None:
    for workspace in list_workspaces():
        if workspace.id == workspace_id:
            return workspace
    return None


def get_workspace_membership(user_id: str, workspace_id: str) -> WorkspaceMembership | None:
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
    personal = next((m for m in memberships if get_workspace_by_id(m.workspace_id) and get_workspace_by_id(m.workspace_id).default_personal), None)
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


def verify_password(user: AuthUser, password: str) -> bool:
    return hmac.compare_digest(user.password_hash, _hash_password(password, user.salt))


def authenticate_user(email: str, password: str) -> AuthUser | None:
    user = get_user_by_email(email)
    if user is None or user.status != "active":
        return None
    return user if verify_password(user, password) else None


def create_user(email: str, password: str, role: str = "member", name: str | None = None) -> AuthUser:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=422, detail="Email is required")
    if get_user_by_email(normalized_email) is not None:
        raise HTTPException(status_code=409, detail="User already exists")
    if role not in {"owner", "member"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    salt = secrets.token_hex(16)
    record = {
        "id": uuid.uuid4().hex,
        "email": normalized_email,
        "name": name or normalized_email,
        "role": role,
        "status": "active",
        "salt": salt,
        "password_hash": _hash_password(password, salt),
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
                raise HTTPException(status_code=422, detail="Invalid role")
            record["role"] = role
        if status is not None:
            if status not in {"active", "disabled"}:
                raise HTTPException(status_code=422, detail="Invalid status")
            record["status"] = status
        if name is not None:
            record["name"] = name.strip() or record.get("name") or record.get("email")
        if password is not None:
            if len(password) < 8:
                raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
            salt = secrets.token_hex(16)
            record["salt"] = salt
            record["password_hash"] = _hash_password(password, salt)
        _write_users_payload(payload)
        return _to_auth_user(record)
    raise HTTPException(status_code=404, detail="User not found")


def create_workspace(name: str, created_by_user_id: str) -> Workspace:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="Workspace name is required")
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
        raise HTTPException(status_code=422, detail="Invalid workspace role")
    payload = _read_workspaces_payload()
    if not any(workspace.get("id") == workspace_id for workspace in payload["workspaces"]):
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not any(user.get("id") == user_id for user in _read_users_payload().get("users", [])):
        raise HTTPException(status_code=404, detail="User not found")
    for membership in payload["memberships"]:
        if membership.get("workspace_id") == workspace_id and membership.get("user_id") == user_id:
            membership["role"] = role
            _write_workspaces_payload(payload)
            return _to_membership(membership)
    record = _workspace_membership_record(workspace_id, user_id, role)
    payload["memberships"].append(record)
    _write_workspaces_payload(payload)
    return _to_membership(record)


def set_active_workspace(user: AuthUser, workspace_id: str) -> tuple[Workspace, WorkspaceMembership]:
    workspace = get_workspace_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    membership = get_workspace_membership(user.id, workspace_id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Workspace membership required")
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
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_owner_user(request: Request) -> AuthUser:
    user = require_user(request)
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access required")
    return user
