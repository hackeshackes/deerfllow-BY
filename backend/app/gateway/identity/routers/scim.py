"""SCIM admin API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.gateway.auth import require_owner_user

router = APIRouter(
    prefix="/api/admin/scim",
    tags=["scim"],
    dependencies=[Depends(require_owner_user)],
)

# Stub state; in production, persisted in DB
_state: dict[str, dict] = {}


@router.get("/state")
async def get_state() -> dict:
    return {"providers": list(_state.values())}


@router.post("/sync/{provider_id}")
async def trigger_sync(provider_id: str) -> dict:
    if provider_id not in _state:
        # Stub: no providers configured yet; idempotent
        return {"status": "noop", "provider_id": provider_id}
    # In production: enqueue a sync task
    return {"status": "queued", "provider_id": provider_id}


@router.put("/state/{provider_id}")
async def update_state(provider_id: str, config: dict) -> dict:
    _state[provider_id] = {
        "provider_id": provider_id,
        **config,
    }
    return _state[provider_id]