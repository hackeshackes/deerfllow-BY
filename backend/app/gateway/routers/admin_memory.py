from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.gateway.abac.deps import require_abac
from app.gateway.auth import AuthUser
from deerflow.agents.memory.updater import get_memory_data

router = APIRouter(prefix="/api/admin/memory", tags=["admin-memory"])


class AdminMemoryResponse(BaseModel):
    user_id: str
    memory: dict


class AdminMemoryListResponse(BaseModel):
    memories: list[AdminMemoryResponse]


@router.get("/users/{user_id}", response_model=AdminMemoryResponse)
async def admin_get_user_memory(
    user_id: str,
    _owner: AuthUser = Depends(require_abac("read", "admin-memory")),
) -> AdminMemoryResponse:
    try:
        memory_data = get_memory_data(user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load memory: {exc}") from exc

    return AdminMemoryResponse(user_id=user_id, memory=memory_data)