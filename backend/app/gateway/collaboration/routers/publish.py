"""FastAPI router for cross-workspace thread publish (v1.6.x B2).

Wired into ``app.py`` via ``app.include_router(router)`` after the lifespan
configures the singleton service with ``configure(PublishService(...))``.

Endpoints:
- ``POST /api/threads/{thread_id}/publish``
- ``GET  /api/threads/{thread_id}/publish-history``
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.gateway.auth import AuthUser, require_user
from app.gateway.collaboration.publish import PublishService

router = APIRouter(prefix="/api/threads", tags=["collaboration"])

_service: PublishService | None = None


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