"""RBAC admin API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/roles", tags=["rbac"])


class RoleIn(BaseModel):
    id: str
    name: str
    scope: str
    description: str | None = None


# In-memory store for stub; replace with DB in subsequent task
_store: dict[str, dict[str, Any]] = {
    "r-admin": {"id": "r-admin", "name": "admin", "scope": "system", "description": "Full access"},
    "r-member": {"id": "r-member", "name": "member", "scope": "system", "description": "Standard member"},
    "r-guest": {"id": "r-guest", "name": "guest", "scope": "system", "description": "Read-only"},
}


@router.get("")
async def list_roles() -> list[dict]:
    return list(_store.values())


@router.post("", status_code=201)
async def create_role(role: RoleIn) -> dict:
    if role.id in _store:
        raise HTTPException(status_code=409, detail="role already exists")
    _store[role.id] = role.model_dump()
    return _store[role.id]


@router.delete("/{role_id}", status_code=204)
async def delete_role(role_id: str) -> None:
    if role_id not in _store:
        raise HTTPException(status_code=404, detail="role not found")
    del _store[role_id]
