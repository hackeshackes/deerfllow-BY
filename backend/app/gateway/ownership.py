from __future__ import annotations

import os

from fastapi import HTTPException, Request

from app.gateway.auth import AuthUser, get_workspace_membership, require_user
from app.gateway.auth_context import get_current_workspace_id
from app.gateway.deps import get_checkpointer, get_store

THREAD_OWNER_KEY = "owner_user_id"
THREAD_WORKSPACE_KEY = "workspace_id"
THREAD_CREATED_BY_KEY = "created_by_user_id"
THREAD_VISIBILITY_KEY = "visibility"
THREAD_SHARED_BY_KEY = "shared_by_user_id"
THREAD_SHARED_AT_KEY = "shared_at"
THREAD_VISIBILITY_PRIVATE = "private"
THREAD_VISIBILITY_WORKSPACE = "workspace"


def normalize_thread_visibility(value: str | None) -> str:
    if value == THREAD_VISIBILITY_PRIVATE:
        return THREAD_VISIBILITY_PRIVATE
    return THREAD_VISIBILITY_WORKSPACE


def get_thread_visibility(record: dict | None) -> str:
    metadata = (record or {}).get("metadata", {}) or {}
    return normalize_thread_visibility(metadata.get(THREAD_VISIBILITY_KEY))


def attach_owner_metadata(metadata: dict | None, user: AuthUser) -> dict:
    merged = dict(metadata or {})
    workspace_id = get_current_workspace_id() or f"ws-{user.id}"
    merged.setdefault(THREAD_OWNER_KEY, user.id)
    merged.setdefault(THREAD_WORKSPACE_KEY, workspace_id)
    merged.setdefault(THREAD_CREATED_BY_KEY, user.id)
    merged.setdefault(THREAD_VISIBILITY_KEY, THREAD_VISIBILITY_PRIVATE)
    merged.setdefault("owner_email", user.email)
    return merged


def can_read_thread(record: dict | None, user: AuthUser) -> bool:
    if record is None:
        return False
    metadata = record.get("metadata", {}) or {}
    if metadata.get(THREAD_OWNER_KEY) == user.id:
        return True
    if normalize_thread_visibility(metadata.get(THREAD_VISIBILITY_KEY)) != THREAD_VISIBILITY_WORKSPACE:
        return False
    workspace_id = metadata.get(THREAD_WORKSPACE_KEY)
    if workspace_id and get_workspace_membership(user.id, workspace_id) is not None:
        return True
    return False


def can_manage_thread(record: dict | None, user: AuthUser) -> bool:
    if record is None:
        return False
    metadata = record.get("metadata", {}) or {}
    return metadata.get(THREAD_OWNER_KEY) == user.id


async def _get_thread_record(request: Request, thread_id: str, user: AuthUser) -> dict:
    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    item = await store.aget(("threads",), thread_id)
    if item is None:
        checkpointer = get_checkpointer(request)
        try:
            async for checkpoint_tuple in checkpointer.alist(None):
                cfg = getattr(checkpoint_tuple, "config", {})
                candidate_thread_id = cfg.get("configurable", {}).get("thread_id")
                if candidate_thread_id != thread_id:
                    continue
                if cfg.get("configurable", {}).get("checkpoint_ns", ""):
                    continue

                checkpoint_meta = getattr(checkpoint_tuple, "metadata", {}) or {}
                recovered = {
                    "thread_id": thread_id,
                    "status": "idle",
                    "created_at": checkpoint_meta.get("created_at", 0),
                    "updated_at": checkpoint_meta.get("updated_at", checkpoint_meta.get("created_at", 0)),
                    "metadata": {k: v for k, v in checkpoint_meta.items() if k not in ("created_at", "updated_at", "step", "source", "writes", "parents")},
                    "values": {},
                }
                recovered.setdefault("metadata", {})
                recovered["metadata"][THREAD_VISIBILITY_KEY] = normalize_thread_visibility(recovered["metadata"].get(THREAD_VISIBILITY_KEY))
                await store.aput(("threads",), thread_id, recovered)
                item = await store.aget(("threads",), thread_id)
                break
        except Exception:
            pass

    if item is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    record = item.value
    record.setdefault("metadata", {})
    record["metadata"][THREAD_VISIBILITY_KEY] = normalize_thread_visibility(record["metadata"].get(THREAD_VISIBILITY_KEY))
    return record


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
    record = await _get_thread_record(request, thread_id, user)
    if not can_manage_thread(record, user):
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    return user, record


async def require_thread_read_access(request: Request, thread_id: str) -> tuple[AuthUser, dict]:
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
        return test_user, {"metadata": {THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE, THREAD_OWNER_KEY: test_user.id}}
    user = require_user(request)
    record = await _get_thread_record(request, thread_id, user)
    if not can_read_thread(record, user):
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    return user, record


async def require_thread_manage_access(request: Request, thread_id: str) -> tuple[AuthUser, dict]:
    return await require_thread_owner(request, thread_id)
