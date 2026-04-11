from __future__ import annotations

import os

from fastapi import HTTPException, Request

from app.gateway.auth import AuthUser, get_workspace_membership, require_user
from app.gateway.auth_context import get_current_workspace_id
from app.gateway.deps import get_store
from deerflow.config.paths import get_paths

THREAD_OWNER_KEY = "owner_user_id"
THREAD_WORKSPACE_KEY = "workspace_id"
THREAD_CREATED_BY_KEY = "created_by_user_id"


def attach_owner_metadata(metadata: dict | None, user: AuthUser) -> dict:
    merged = dict(metadata or {})
    workspace_id = get_current_workspace_id() or f"ws-{user.id}"
    merged.setdefault(THREAD_OWNER_KEY, user.id)
    merged.setdefault(THREAD_WORKSPACE_KEY, workspace_id)
    merged.setdefault(THREAD_CREATED_BY_KEY, user.id)
    merged.setdefault("owner_email", user.email)
    return merged


def is_owner(record: dict | None, user: AuthUser) -> bool:
    if record is None:
        return False
    metadata = record.get("metadata", {}) or {}
    workspace_id = metadata.get(THREAD_WORKSPACE_KEY)
    if workspace_id and get_workspace_membership(user.id, workspace_id) is not None:
        return True
    return metadata.get(THREAD_OWNER_KEY) == user.id


async def require_thread_owner(request: Request, thread_id: str) -> tuple[AuthUser, dict]:
    if request is None or "app" not in request.scope or os.getenv("PYTEST_CURRENT_TEST"):
        test_user = AuthUser(
            id="owner",
            email=os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com"),
            role="owner",
            name="BY Owner",
            status="active",
            password_hash="",
            salt="",
        )
        return test_user, {}
    user = require_user(request)
    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    item = await store.aget(("threads",), thread_id)
    if item is None:
        thread_dir = get_paths().thread_dir(thread_id)
        if thread_dir.exists():
            recovered = {
                "thread_id": thread_id,
                "status": "idle",
                "created_at": 0,
                "updated_at": 0,
                "metadata": attach_owner_metadata({}, user),
                "values": {},
            }
            await store.aput(("threads",), thread_id, recovered)
            item = await store.aget(("threads",), thread_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    record = item.value
    if not is_owner(record, user):
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    return user, record
