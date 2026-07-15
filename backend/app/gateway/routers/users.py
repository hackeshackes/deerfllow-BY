from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.gateway.auth import (
    SESSION_COOKIE_NAME,
    AuthUser,
    InviteToken,
    Workspace,
    WorkspaceMembership,
    activate_user_from_token,
    add_workspace_member,
    authenticate_user,
    change_user_password,
    create_session_token,
    create_user,
    create_workspace,
    delete_user,
    delete_workspace,
    get_active_invite_for_user,
    get_default_workspace_id_for_user,
    get_user_by_email,
    get_user_by_id,
    get_workspace_by_id,
    get_workspace_membership,
    issue_invite_token,
    list_users,
    list_workspace_memberships,
    list_workspaces,
    list_workspaces_for_user,
    remove_workspace_member,
    require_owner_user,
    require_user,
    set_active_workspace,
    touch_last_login,
    update_user,
    update_workspace,
)
from deerflow.admin import append_admin_audit_record
from deerflow.config.paths import get_paths

router = APIRouter(prefix="/api", tags=["users"])


class SessionLoginRequest(BaseModel):
    email: str
    password: str


class SessionUserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    status: str
    invited_at: str | None = None
    activated_at: str | None = None
    last_login_at: str | None = None
    active_workspace_id: str | None = None
    active_workspace_name: str | None = None
    active_workspace_role: str | None = None


class InviteResponse(BaseModel):
    token: str
    expires_at: str
    activation_path: str


class UserResponse(SessionUserResponse):
    invite: InviteResponse | None = None


class UsersListResponse(BaseModel):
    users: list[UserResponse]


class UserCreateRequest(BaseModel):
    email: str
    role: str = "member"
    name: str | None = None


class UserUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None
    name: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserInviteRequest(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class UserDeleteResponse(BaseModel):
    success: bool
    message: str


class AccountPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ActivationRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_by_user_id: str
    default_personal: bool
    role: str
    member_count: int
    thread_count: int = 0
    upload_file_count: int = 0
    artifact_file_count: int = 0
    agent_count: int = 0
    members: list[dict[str, str]] = Field(default_factory=list)


class WorkspacesListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class WorkspaceCreateRequest(BaseModel):
    name: str


class WorkspaceMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(min_length=1)


class WorkspaceDeleteResponse(BaseModel):
    success: bool
    message: str


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: str


def _invite_to_response(invite: InviteToken | None) -> InviteResponse | None:
    if invite is None:
        return None
    return InviteResponse(
        token=invite.token,
        expires_at=invite.expires_at,
        activation_path=f"/activate?token={invite.token}",
    )


def _mask_email(email: str) -> str:
    """Partially mask an email address for display to non-owners.

    Example: `john.doe@example.com` -> `j******e@example.com`
    """
    if not email or "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(len(local) - 1, 1)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _to_workspace_response(workspace: Workspace, membership: WorkspaceMembership, viewer_role: str | None = None) -> WorkspaceResponse:
    workspace_dir = get_paths().workspace_dir(workspace.id)
    threads_dir = workspace_dir / "threads"
    agents_dir = workspace_dir / "agents"
    thread_count = sum(1 for item in threads_dir.iterdir() if item.is_dir()) if threads_dir.exists() else 0
    upload_file_count = _count_files_under_many(thread_dir / "user-data" / "uploads" for thread_dir in threads_dir.iterdir() if thread_dir.is_dir()) if threads_dir.exists() else 0
    artifact_file_count = _count_files_under_many(thread_dir / "user-data" / "outputs" for thread_dir in threads_dir.iterdir() if thread_dir.is_dir()) if threads_dir.exists() else 0
    workspace_memberships = [item for item in list_workspace_memberships() if item.workspace_id == workspace.id]
    member_count = len(workspace_memberships)
    # Only owners see raw email addresses of workspace members; everyone else
    # gets a partially masked value to avoid PII leakage.
    can_see_email = (viewer_role == "owner")
    members = []
    for workspace_membership in workspace_memberships:
        member_user = get_user_by_id(workspace_membership.user_id)
        if member_user is None:
            continue
        members.append(
            {
                "id": member_user.id,
                "name": member_user.name,
                "email": member_user.email if can_see_email else _mask_email(member_user.email),
                "role": workspace_membership.role,
            }
        )
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        created_by_user_id=workspace.created_by_user_id,
        default_personal=workspace.default_personal,
        role=membership.role,
        member_count=member_count,
        thread_count=thread_count,
        upload_file_count=upload_file_count,
        artifact_file_count=artifact_file_count,
        agent_count=sum(1 for item in agents_dir.iterdir() if item.is_dir()) if agents_dir.exists() else 0,
        members=members,
    )


def _count_files_under_many(paths: list[Path] | tuple[Path, ...] | object) -> int:
    total = 0
    for path in paths:
        if not isinstance(path, Path) or not path.exists():
            continue
        total += sum(1 for item in path.rglob("*") if item.is_file())
    return total


def _to_response(user: AuthUser, active_workspace_id: str | None = None) -> SessionUserResponse:
    workspace_id = active_workspace_id or get_default_workspace_id_for_user(user.id)
    workspace = get_workspace_by_id(workspace_id) if workspace_id else None
    membership = get_workspace_membership(user.id, workspace_id) if workspace_id else None
    return SessionUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        name=user.name,
        status=user.status,
        invited_at=user.invited_at,
        activated_at=user.activated_at,
        last_login_at=user.last_login_at,
        active_workspace_id=workspace_id,
        active_workspace_name=workspace.name if workspace else None,
        active_workspace_role=membership.role if membership else None,
    )


def _to_user_response(user: AuthUser, active_workspace_id: str | None = None, include_invite: bool = False) -> UserResponse:
    base = _to_response(user, active_workspace_id=active_workspace_id)
    # Only expose the invite token when the caller explicitly asks for it
    # (i.e. just created/resent an invite). Listing users never includes the
    # token to prevent it from leaking through logs or intermediary caches.
    invite = (
        _invite_to_response(get_active_invite_for_user(user.id))
        if include_invite and user.status == "invited"
        else None
    )
    return UserResponse(**base.model_dump(), invite=invite)


def _use_secure_cookie(request: Request | None = None) -> bool:
    """Decide whether to set the session cookie with the Secure flag.

    Trusts the configured deployment mode (``BY_FORCE_SECURE_COOKIE``) over the
    incoming ``X-Forwarded-Proto`` header — the latter can be spoofed by an
    attacker on the same network to convince the gateway that the connection
    is HTTPS even when it isn't.
    """
    # Operator opt-in: require Secure regardless of header state. Recommended
    # in any deployment that fronts the gateway with HTTPS.
    forced = os.getenv("BY_FORCE_SECURE_COOKIE", "").lower() in {"1", "true", "yes"}
    if forced:
        return True
    if request is not None:
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto.lower() == "https":
            return True
    return False


def _set_session_cookie(response: Response, user: AuthUser, request: Request, *, active_workspace_id: str | None = None) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(user, active_workspace_id=active_workspace_id),
        httponly=True,
        samesite="lax",
        secure=_use_secure_cookie(request),
        path="/",
        max_age=60 * 60 * 24 * 14,
    )


@router.post("/session/login", response_model=SessionUserResponse)
async def login(body: SessionLoginRequest, response: Response, request: Request) -> SessionUserResponse:
    user = get_user_by_email(body.email)
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if user.status == "invited":
        raise HTTPException(status_code=403, detail="账号尚未激活，请先完成邀请激活")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="账号已被禁用")

    authenticated = authenticate_user(body.email, body.password)
    if authenticated is None:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    touch_last_login(authenticated.id)
    refreshed = get_user_by_email(authenticated.email) or authenticated
    active_workspace_id = get_default_workspace_id_for_user(refreshed.id)
    _set_session_cookie(response, refreshed, request, active_workspace_id=active_workspace_id)
    return _to_response(refreshed, active_workspace_id=active_workspace_id)


@router.post("/session/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/session/me", response_model=SessionUserResponse)
async def session_me(request: Request) -> SessionUserResponse:
    user = require_user(request)
    active_workspace_id = getattr(request.state, "active_workspace_id", None)
    return _to_response(user, active_workspace_id=active_workspace_id)


@router.get("/users/me", response_model=SessionUserResponse)
async def get_me(request: Request) -> SessionUserResponse:
    user = require_user(request)
    active_workspace_id = getattr(request.state, "active_workspace_id", None)
    return _to_response(user, active_workspace_id=active_workspace_id)


@router.post("/users/activate", response_model=SessionUserResponse)
async def activate_user_endpoint(body: ActivationRequest, response: Response, request: Request) -> SessionUserResponse:
    user = activate_user_from_token(body.token, body.password)
    touch_last_login(user.id)
    refreshed = get_user_by_email(user.email) or user
    active_workspace_id = get_default_workspace_id_for_user(refreshed.id)
    _set_session_cookie(response, refreshed, request, active_workspace_id=active_workspace_id)
    return _to_response(refreshed, active_workspace_id=active_workspace_id)


@router.post("/account/change-password", response_model=SessionUserResponse)
async def change_password_endpoint(body: AccountPasswordChangeRequest, request: Request) -> SessionUserResponse:
    user = require_user(request)
    updated = change_user_password(user.id, body.current_password, body.new_password)
    active_workspace_id = getattr(request.state, "active_workspace_id", None)
    return _to_response(updated, active_workspace_id=active_workspace_id)


@router.get("/users", response_model=UsersListResponse)
async def get_users(
    request: Request,
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> UsersListResponse:
    require_owner_user(request)
    users = list_users()
    if role is not None:
        users = [user for user in users if user.role == role]
    if status is not None:
        users = [user for user in users if user.status == status]
    return UsersListResponse(users=[_to_user_response(user) for user in users])


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_endpoint(
    body: UserCreateRequest,
    request: Request,
    include_invite: bool = Query(default=False, description="If true, returns the activation token in the invite field. Defaults to false to avoid leaking the token via logs."),
) -> UserResponse:
    actor = require_owner_user(request)
    user = create_user(body.email, role=body.role, name=body.name, status="invited")
    issue_invite_token(user.id)
    append_admin_audit_record("user.created", actor_id=actor.id, target=user.id, details={"email": user.email, "role": user.role})
    return _to_user_response(user, include_invite=include_invite)


@router.post("/users/{user_id}/invite", response_model=UserResponse)
async def resend_invite_endpoint(
    user_id: str,
    body: UserInviteRequest,
    request: Request,
    include_invite: bool = Query(default=False, description="If true, returns the activation token in the invite field. Defaults to false to avoid leaking the token via logs."),
) -> UserResponse:
    actor = require_owner_user(request)
    user = update_user(user_id, status="invited")
    issue_invite_token(user.id, expires_in_hours=body.expires_in_hours)
    refreshed = get_user_by_email(user.email) or user
    append_admin_audit_record("user.reinvited", actor_id=actor.id, target=user.id, details={"expires_in_hours": body.expires_in_hours})
    return _to_user_response(refreshed, include_invite=include_invite)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(user_id: str, body: UserUpdateRequest, request: Request) -> UserResponse:
    actor = require_owner_user(request)
    updated = update_user(user_id, role=body.role, status=body.status, name=body.name, password=body.password)
    append_admin_audit_record(
        "user.updated",
        actor_id=actor.id,
        target=updated.id,
        details={"role": body.role, "status": body.status, "name": body.name, "password_updated": body.password is not None},
    )
    return _to_user_response(updated)


@router.delete("/users/{user_id}", response_model=UserDeleteResponse)
async def delete_user_endpoint(user_id: str, request: Request) -> UserDeleteResponse:
    actor = require_owner_user(request)
    deleted = delete_user(user_id, actor_user_id=actor.id)
    append_admin_audit_record(
        "user.deleted",
        actor_id=actor.id,
        target=deleted.id,
        details={"email": deleted.email, "role": deleted.role},
    )
    return UserDeleteResponse(success=True, message=f"用户 {deleted.email} 已删除")


@router.get("/workspaces", response_model=WorkspacesListResponse)
async def get_workspaces(request: Request) -> WorkspacesListResponse:
    user = require_user(request)
    if user.role == "owner":
        workspaces = []
        for workspace in list_workspaces():
            membership = get_workspace_membership(user.id, workspace.id) or WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner")
            workspaces.append(_to_workspace_response(workspace, membership, viewer_role=user.role))
        return WorkspacesListResponse(workspaces=workspaces)

    memberships = list_workspaces_for_user(user.id)
    workspaces = []
    for membership in memberships:
        workspace = get_workspace_by_id(membership.workspace_id)
        if workspace is not None:
            workspaces.append(_to_workspace_response(workspace, membership, viewer_role=user.role))
    return WorkspacesListResponse(workspaces=workspaces)


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace_endpoint(body: WorkspaceCreateRequest, request: Request) -> WorkspaceResponse:
    actor = require_owner_user(request)
    workspace = create_workspace(body.name, actor.id)
    membership = get_workspace_membership(actor.id, workspace.id)
    append_admin_audit_record("workspace.created", actor_id=actor.id, target=workspace.id, details={"name": workspace.name})
    return _to_workspace_response(workspace, membership, viewer_role=actor.role)


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceResponse)
async def add_workspace_member_endpoint(workspace_id: str, body: WorkspaceMemberRequest, request: Request) -> WorkspaceResponse:
    actor = require_owner_user(request)
    membership = add_workspace_member(workspace_id, body.user_id, role=body.role)
    workspace = get_workspace_by_id(workspace_id)
    append_admin_audit_record("workspace.member_added", actor_id=actor.id, target=workspace_id, details={"user_id": body.user_id, "role": body.role})
    return _to_workspace_response(workspace, membership, viewer_role=actor.role)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace_endpoint(workspace_id: str, body: WorkspaceUpdateRequest, request: Request) -> WorkspaceResponse:
    actor = require_owner_user(request)
    workspace = update_workspace(workspace_id, name=body.name)
    membership = get_workspace_membership(actor.id, workspace.id)
    append_admin_audit_record("workspace.updated", actor_id=actor.id, target=workspace_id, details={"name": workspace.name})
    return _to_workspace_response(workspace, membership, viewer_role=actor.role)


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceDeleteResponse)
async def delete_workspace_endpoint(workspace_id: str, request: Request) -> WorkspaceDeleteResponse:
    actor = require_owner_user(request)
    deleted = delete_workspace(workspace_id)
    append_admin_audit_record("workspace.deleted", actor_id=actor.id, target=workspace_id, details={"name": deleted.name})
    return WorkspaceDeleteResponse(success=True, message=f"空间 {deleted.name} 已删除")


@router.delete("/workspaces/{workspace_id}/members/{user_id}", response_model=WorkspaceResponse)
async def remove_workspace_member_endpoint(workspace_id: str, user_id: str, request: Request) -> WorkspaceResponse:
    actor = require_owner_user(request)
    removed = remove_workspace_member(workspace_id, user_id)
    workspace = get_workspace_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="未找到该空间")
    append_admin_audit_record("workspace.member_removed", actor_id=actor.id, target=workspace_id, details={"user_id": removed.user_id})
    membership = get_workspace_membership(actor.id, workspace_id)
    return _to_workspace_response(workspace, membership, viewer_role=actor.role)


@router.post("/session/workspace", response_model=SessionUserResponse)
async def switch_workspace(body: WorkspaceSwitchRequest, response: Response, request: Request) -> SessionUserResponse:
    user = require_user(request)
    workspace, _membership = set_active_workspace(user, body.workspace_id)
    _set_session_cookie(response, user, request, active_workspace_id=workspace.id)
    return _to_response(user, active_workspace_id=workspace.id)
