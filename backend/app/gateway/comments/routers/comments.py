"""Comments HTTP endpoints (v1.5.8).

Wires the in-memory ``InMemoryCommentStore`` to FastAPI. Persistence
layer (SQLite-backed) is added in v1.5.9+ via
``backend/app/gateway/data/migrations/004_v1.5.8.sql``.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.comments.models import Comment
from app.gateway.comments.service import InMemoryCommentStore


def _get_store(request: Request) -> InMemoryCommentStore:
    """Resolve the singleton store from ``app.state``.

    Falls back to a fresh in-memory store when ``app.state.comments_store``
    is not set (e.g. tests, cold-start edge cases). The fallback means
    comments posted via this fallback don't survive across processes or
    restarts — which is the documented v1.5.8 behaviour.
    """
    store = getattr(request.app.state, "comments_store", None)
    if store is None:
        store = InMemoryCommentStore()
    return store


router = APIRouter(prefix="/api/threads", tags=["comments"])


class CreateCommentRequest(BaseModel):
    """Wire format clients POST to create a comment."""

    text: str = Field(..., min_length=1, max_length=4000)
    parent_comment_id: Optional[str] = None
    source: Optional[str] = None  # "user" (default) / "agent" / "automation"


class CommentResponse(BaseModel):
    """Wire format clients see. Mirrors the domain dataclass."""

    id: str
    thread_id: str
    author_id: str
    text: str
    source: str
    parent_comment_id: Optional[str] = None
    mentioned_user_ids: list[str] = Field(default_factory=list)
    created_at: str

    @classmethod
    def from_model(cls, c: Comment) -> "CommentResponse":
        return cls(
            id=c.id,
            thread_id=c.thread_id,
            author_id=c.author_id,
            text=c.text,
            source=c.source.value if hasattr(c.source, "value") else str(c.source),
            parent_comment_id=c.parent_comment_id,
            mentioned_user_ids=list(c.mentioned_user_ids or []),
            created_at=c.created_at,
        )


@router.get("/{thread_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    thread_id: str,
    request: Request,
    user: dict = Depends(require_user),
) -> list[CommentResponse]:
    """List the most recent (≤100) comments for a thread."""
    store = _get_store(request)
    items = store.list_for_thread(thread_id)
    return [CommentResponse.from_model(c) for c in items]


@router.post(
    "/{thread_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def create_comment(
    thread_id: str,
    payload: CreateCommentRequest,
    request: Request,
    user: dict = Depends(require_user),
) -> CommentResponse:
    """Create a new comment under a thread.

    The author is resolved from ``user["email"]`` (falling back to
    ``user["id"]``) so a UI client doesn't need to know how auth works.
    """
    store = _get_store(request)
    author_id = user.email or user.id or "unknown"
    comment = store.add(
        thread_id=thread_id,
        author_id=author_id,
        text=payload.text,
        parent_comment_id=payload.parent_comment_id,
    )
    return CommentResponse.from_model(comment)


@router.delete(
    "/{thread_id}/comments/{comment_id}",
    status_code=204,
)
async def delete_comment(
    thread_id: str,
    comment_id: str,
    request: Request,
    user: dict = Depends(require_user),
) -> None:
    """Delete a single comment. Only the author can delete their own."""
    store = _get_store(request)
    existing = store.get(comment_id)
    if existing is None or existing.thread_id != thread_id:
        raise HTTPException(status_code=404, detail="comment not found")
    if existing.author_id != (user.email or user.id):
        raise HTTPException(
            status_code=403, detail="cannot delete another user's comment",
        )
    if not store.delete(comment_id):
        raise HTTPException(status_code=404, detail="comment not found")
