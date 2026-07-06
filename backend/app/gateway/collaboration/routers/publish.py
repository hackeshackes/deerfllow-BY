"""FastAPI router for cross-workspace thread publish (v1.6.x).

NOT YET WIRED into ``app.py``. This file exists so that:

- The route shape is documented and reviewable.
- A future integration task can wire it via ``app.include_router(router)``
  plus a ``configure(...)`` call during app startup.
- Tests can exercise the routes in isolation by setting the singleton
  via :func:`configure` and then mounting the router on a test app.

Endpoints:
- ``POST /api/threads/{thread_id}/publish``
- ``GET  /api/threads/{thread_id}/publish-history``
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.gateway.auth import AuthUser, require_user
from app.gateway.collaboration.publish import PublishService

router = APIRouter(prefix="/api/threads", tags=["collaboration"])

_service: PublishService | None = None


def configure(service: PublishService) -> None:
    """Wire the PublishService. Called from app.py lifespan (future integration)."""
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
def publish_thread(
    thread_id: str,
    body: _PublishBody,
    user: AuthUser = Depends(require_user),
    svc: PublishService = Depends(_dep_service),
) -> _PublishResponse:
    try:
        result = svc.publish(thread_id, body.target_workspace_id, actor_user_id=user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _PublishResponse(
        new_thread_id=result.new_thread_id,
        source_thread_id=result.source_thread_id,
        target_workspace_id=result.target_workspace_id,
        original_thread_id=result.original_thread_id,
        published_at=result.published_at,
    )


@router.get("/{thread_id}/publish-history", response_model=dict)
def publish_history(
    thread_id: str,
    user: AuthUser = Depends(require_user),
    svc: PublishService = Depends(_dep_service),
) -> dict:
    return {"events": [e.__dict__ for e in svc.history(thread_id)]}
