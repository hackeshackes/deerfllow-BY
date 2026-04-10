from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
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
    get_active_invite_for_user,
    get_default_workspace_id_for_user,
    get_user_by_email,
    get_workspace_by_id,
    get_workspace_membership,
    issue_invite_token,
    list_users,
    list_workspaces_for_user,
    require_owner_user,
    require_user,
    set_active_workspace,
    touch_last_login,
    update_user,
)

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


class WorkspacesListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class WorkspaceCreateRequest(BaseModel):
    name: str


class WorkspaceMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


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


def _to_workspace_response(workspace: Workspace, membership: WorkspaceMembership) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        created_by_user_id=workspace.created_by_user_id,
        default_personal=workspace.default_personal,
        role=membership.role,
    )


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


def _to_user_response(user: AuthUser, active_workspace_id: str | None = None) -> UserResponse:
    base = _to_response(user, active_workspace_id=active_workspace_id)
    invite = _invite_to_response(get_active_invite_for_user(user.id)) if user.status == "invited" else None
    return UserResponse(**base.model_dump(), invite=invite)


def _use_secure_cookie(request: Request | None = None) -> bool:
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
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status == "invited":
        raise HTTPException(status_code=403, detail="Account has not been activated yet")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="Account is disabled")

    authenticated = authenticate_user(body.email, body.password)
    if authenticated is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
async def get_users(request: Request) -> UsersListResponse:
    require_owner_user(request)
    return UsersListResponse(users=[_to_user_response(user) for user in list_users()])


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_endpoint(body: UserCreateRequest, request: Request) -> UserResponse:
    require_owner_user(request)
    user = create_user(body.email, role=body.role, name=body.name, status="invited")
    issue_invite_token(user.id)
    return _to_user_response(user)


@router.post("/users/{user_id}/invite", response_model=UserResponse)
async def resend_invite_endpoint(user_id: str, body: UserInviteRequest, request: Request) -> UserResponse:
    require_owner_user(request)
    user = update_user(user_id, status="invited")
    issue_invite_token(user.id, expires_in_hours=body.expires_in_hours)
    refreshed = get_user_by_email(user.email) or user
    return _to_user_response(refreshed)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(user_id: str, body: UserUpdateRequest, request: Request) -> UserResponse:
    require_owner_user(request)
    updated = update_user(user_id, role=body.role, status=body.status, name=body.name, password=body.password)
    return _to_user_response(updated)


@router.get("/workspaces", response_model=WorkspacesListResponse)
async def get_workspaces(request: Request) -> WorkspacesListResponse:
    user = require_user(request)
    memberships = list_workspaces_for_user(user.id)
    workspaces = []
    for membership in memberships:
        workspace = get_workspace_by_id(membership.workspace_id)
        if workspace is not None:
            workspaces.append(_to_workspace_response(workspace, membership))
    return WorkspacesListResponse(workspaces=workspaces)


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace_endpoint(body: WorkspaceCreateRequest, request: Request) -> WorkspaceResponse:
    user = require_owner_user(request)
    workspace = create_workspace(body.name, user.id)
    membership = get_workspace_membership(user.id, workspace.id)
    return _to_workspace_response(workspace, membership)


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceResponse)
async def add_workspace_member_endpoint(workspace_id: str, body: WorkspaceMemberRequest, request: Request) -> WorkspaceResponse:
    require_owner_user(request)
    membership = add_workspace_member(workspace_id, body.user_id, role=body.role)
    workspace = get_workspace_by_id(workspace_id)
    return _to_workspace_response(workspace, membership)


@router.post("/session/workspace", response_model=SessionUserResponse)
async def switch_workspace(body: WorkspaceSwitchRequest, response: Response, request: Request) -> SessionUserResponse:
    user = require_user(request)
    workspace, _membership = set_active_workspace(user, body.workspace_id)
    _set_session_cookie(response, user, request, active_workspace_id=workspace.id)
    return _to_response(user, active_workspace_id=workspace.id)
