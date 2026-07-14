"""FastAPI router for cross-workspace thread publish (v1.6.x B2).

Wired into ``app.py`` via ``app.include_router(router)`` after the lifespan
configures the singleton service with ``configure(PublishService(...))``.

Endpoints:
- ``POST /api/threads/{thread_id}/publish``
- ``GET  /api/threads/{thread_id}/publish-history``

v1.6.1: publish is gated by ABAC (``OwnerOnlyPolicy`` +
``WorkspaceMemberPolicy``) so authorization lives next to the route
and reads as data instead of an inline role check.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.gateway.abac import (
    Action,
    OwnerOnlyPolicy,
    Resource,
    Subject,
    WorkspaceMemberPolicy,
    evaluate,
)
from app.gateway.auth import (
    AuthUser,
    list_workspaces_for_user,
    require_user,
)
from app.gateway.collaboration.publish import PublishService

router = APIRouter(prefix="/api/threads", tags=["collaboration"])

_service: PublishService | None = None

# ABAC policies applied at the route boundary (v1.6.1). The list is
# small today but iterable so future policies (e.g. "publish must
# land in a workspace the actor has 'admin' role on") can be added
# without changing the call site.
_PUBLISH_POLICIES = (
    OwnerOnlyPolicy(verbs=("publish",)),
    WorkspaceMemberPolicy(verbs=("publish",)),
)


def configure(service: PublishService) -> None:
    """Wire the PublishService. Called from app.py lifespan."""
    global _service
    _service = service


def reset_for_tests() -> None:
    """Clear the wired service. Tests should call this in teardown."""
    global _service
    _service = None


def _dep_service() -> PublishService:
    if _service is None:
        raise HTTPException(status_code=503, detail="publish service not configured")
    return _service


def _subject_for(user: AuthUser) -> Subject:
    """Build the ABAC Subject from the authenticated AuthUser."""
    memberships = list_workspaces_for_user(user.id)
    return Subject(
        id=user.id,
        role=user.role,
        attrs={"workspaces": [m.workspace_id for m in memberships]},
    )


class _PublishBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_workspace_id: str


class _PublishResponse(BaseModel):
    new_thread_id: str
    source_thread_id: str
    target_workspace_id: str
    original_thread_id: str
    published_at: datetime


@router.post("/{thread_id}/publish", response_model=_PublishResponse)
async def publish_thread(
    thread_id: str,
    body: _PublishBody,
    request: Request,
    user: AuthUser = Depends(require_user),
    svc: PublishService = Depends(_dep_service),
) -> _PublishResponse:
    # Touch the request so FastAPI doesn't strip it; also useful for future
    # request-scoped tracing.
    _ = request
    # ABAC (v1.6.1): evaluating the policy here lets us deny before
    # the service does its (more expensive) thread lookup. The
    # resource attributes project only the fields the policies need
    # so we don't leak unrelated domain state into the evaluator.
    resource = Resource(
        type="thread",
        id=thread_id,
        attrs={"workspace_id": getattr(user, "active_workspace_id", "") or ""},
    )
    decision = evaluate(
        subject=_subject_for(user),
        resource=resource,
        action=Action(verb="publish"),
        policies=_PUBLISH_POLICIES,
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    try:
        result = await svc.publish(thread_id, body.target_workspace_id, actor_user_id=user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _PublishResponse(
        new_thread_id=result.new_thread_id,
        source_thread_id=result.source_thread_id,
        target_workspace_id=result.target_workspace_id,
        original_thread_id=result.original_thread_id,
        published_at=result.published_at,
    )


@router.get("/{thread_id}/publish-history", response_model=dict)
async def publish_history(
    thread_id: str,
    request: Request,
    user: AuthUser = Depends(require_user),
    svc: PublishService = Depends(_dep_service),
) -> dict:
    _ = request
    events = await svc.history(thread_id)
    return {
        "events": [
            {
                "new_thread_id": e.new_thread_id,
                "target_workspace_id": e.target_workspace_id,
                "actor_user_id": e.actor_user_id,
                "at": e.at,
            }
            for e in events
        ]
    }