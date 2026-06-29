"""Subscriptions API.

Endpoints:
- `POST   /api/subscriptions`                      — subscribe to a target
- `DELETE /api/subscriptions/{kind}/{id}`          — unsubscribe (all subs for target)
- `GET    /api/subscriptions/{kind}/{id}/count`    — fan-out size for a target

Stub auth: the `user_id` is hard-coded as `"current-user"`. A follow-up will
read it from the session context (see CLAUDE.md auth conventions).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import NotifyChannel, Subscription, SubscriptionTarget
from ..service import InMemorySubscriptionStore

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

# In-memory store; production swaps this for a Postgres-backed one.
_store = InMemorySubscriptionStore()
_CURRENT_USER = "current-user"  # stub


def _reset_store() -> None:
    """Reset the in-memory store — used by tests to isolate state."""
    global _store
    _store = InMemorySubscriptionStore()


class SubscriptionIn(BaseModel):
    target_kind: str = Field(..., description="thread|knowledge|automation|...")
    target_id: str = Field(..., min_length=1)
    notify_via: list[str] = Field(
        default_factory=lambda: [NotifyChannel.INAPP.value],
        description="Channels to notify on (inapp|email|feishu|dingtalk)",
    )


class SubscriptionOut(BaseModel):
    id: str
    user_id: str
    target_kind: str
    target_id: str
    notify_via: list[str]


def _next_id() -> str:
    """Generate a unique subscription id."""
    import uuid
    return f"sub-{uuid.uuid4().hex[:12]}"


@router.post("", status_code=201, response_model=SubscriptionOut)
async def subscribe(data: SubscriptionIn) -> SubscriptionOut:
    try:
        target = SubscriptionTarget(kind=data.target_kind, id=data.target_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        channels = [NotifyChannel(c) for c in data.notify_via]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"invalid notify_via: {e}")

    sub = Subscription(
        id=_next_id(),
        user_id=_CURRENT_USER,
        target=target,
        notify_via=channels,
    )
    await _store.add(sub)
    return SubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        target_kind=sub.target.kind,
        target_id=sub.target.id,
        notify_via=[c.value for c in sub.notify_via],
    )


@router.delete("/{target_kind}/{target_id}", status_code=204)
async def unsubscribe(target_kind: str, target_id: str) -> None:
    try:
        target = SubscriptionTarget(kind=target_kind, id=target_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await _store.remove(target)


@router.get("/{target_kind}/{target_id}/count")
async def count_subscribers(target_kind: str, target_id: str) -> dict:
    try:
        target = SubscriptionTarget(kind=target_kind, id=target_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    subs = await _store.get_for_target(target)
    return {"count": len(subs)}
