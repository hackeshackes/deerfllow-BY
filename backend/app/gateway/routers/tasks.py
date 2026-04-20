"""Scheduled Tasks API - CRUD, sharing and execution endpoints with SQLite persistence."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.auth_context import get_current_workspace_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_db_path = Path(__file__).parent.parent / "data" / "tasks.db"
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock:
        conn = _get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_id TEXT,
                visibility TEXT DEFAULT 'private',
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                prompt_template TEXT NOT NULL,
                model_name TEXT,
                skill_names TEXT NOT NULL DEFAULT '[]',
                notification_config TEXT NOT NULL DEFAULT '{}',
                output_config TEXT NOT NULL DEFAULT '{}',
                status TEXT DEFAULT 'active',
                next_run_at TEXT,
                last_run_at TEXT,
                thread_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                thread_id TEXT,
                status TEXT NOT NULL,
                started_at REAL,
                completed_at REAL,
                result_summary TEXT,
                error_message TEXT,
                token_used INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS task_shares (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                target_workspace_id TEXT NOT NULL,
                permission TEXT DEFAULT 'read',
                shared_by TEXT NOT NULL,
                shared_at REAL NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(task_id, target_workspace_id)
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions(task_id);
            CREATE INDEX IF NOT EXISTS idx_task_shares_task_id ON task_shares(task_id);
        """)
        # Migration: add thread_id column if it doesn't exist (for existing databases)
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN thread_id TEXT")
            conn.commit()
        except Exception:
            pass  # Column already exists
        conn.close()


_init_db()


class TriggerConfig(BaseModel):
    cron: str | None = None
    interval_seconds: int | None = None
    interval_minutes: int | None = None
    interval_hours: int | None = None
    interval_days: int | None = None
    timezone: str = "Asia/Shanghai"
    start_date: str | None = None
    end_date: str | None = None


class NotificationConfig(BaseModel):
    enabled: bool = True
    channels: list[str] = ["in_app"]


class OutputConfig(BaseModel):
    save_to_thread: bool = True
    webhook_url: str | None = None


class TaskCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str
    trigger_config: TriggerConfig
    prompt_template: str = Field(min_length=1)
    model_name: str | None = None
    skill_names: list[str] = []
    notification_config: NotificationConfig = NotificationConfig()
    output_config: OutputConfig = OutputConfig()


class TaskUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str | None = None
    trigger_config: TriggerConfig | None = None
    prompt_template: str | None = Field(default=None, min_length=1)
    model_name: str | None = None
    skill_names: list[str] | None = None
    notification_config: NotificationConfig | None = None
    output_config: OutputConfig | None = None
    status: str | None = None


class TaskShareRequest(BaseModel):
    target_workspace_id: str
    permission: str = "read"


class TaskResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str | None = None
    visibility: str = "private"
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict[str, Any]
    prompt_template: str
    model_name: str | None = None
    skill_names: list[str] = []
    notification_config: dict[str, Any]
    output_config: dict[str, Any]
    status: str
    next_run_at: str | None = None
    last_run_at: str | None = None
    created_at: str
    updated_at: str
    shared_to: list[str] = []
    thread_id: str | None = None


class TaskExecutionResponse(BaseModel):
    id: str
    task_id: str
    thread_id: str | None = None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    result_summary: str | None = None
    error_message: str | None = None
    token_used: int = 0


class ShareResponse(BaseModel):
    id: str
    task_id: str
    target_workspace_id: str
    permission: str
    shared_by: str
    shared_at: str


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "workspace_id": row["workspace_id"],
        "visibility": row["visibility"],
        "name": row["name"],
        "description": row["description"],
        "trigger_type": row["trigger_type"],
        "trigger_config": json.loads(row["trigger_config"]),
        "prompt_template": row["prompt_template"],
        "model_name": row["model_name"],
        "skill_names": json.loads(row["skill_names"]),
        "notification_config": json.loads(row["notification_config"]),
        "output_config": json.loads(row["output_config"]),
        "status": row["status"],
        "next_run_at": row["next_run_at"],
        "last_run_at": row["last_run_at"],
        "thread_id": row["thread_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _calculate_next_run(trigger_type: str, trigger_config: dict) -> str | None:
    import datetime

    try:
        if trigger_type == "cron" and trigger_config.get("cron"):
            return None
        elif trigger_type == "interval":
            interval_seconds = (
                trigger_config.get("interval_seconds")
                or (trigger_config.get("interval_minutes", 0) * 60)
                or (trigger_config.get("interval_hours", 0) * 3600)
                or (trigger_config.get("interval_days", 0) * 86400)
                or 0
            )
            if interval_seconds > 0:
                next_run = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=interval_seconds)
                return next_run.isoformat()
        return None
    except Exception:
        return None


def _validate_trigger_config(trigger_type: str, trigger_config: TriggerConfig) -> None:
    if trigger_type == "cron":
        if not trigger_config.cron:
            raise HTTPException(status_code=422, detail="Cron expression required for cron trigger")
        parts = trigger_config.cron.split()
        if len(parts) != 5:
            raise HTTPException(status_code=422, detail="Invalid cron expression: must have 5 fields")
    elif trigger_type == "interval":
        has_interval = (
            trigger_config.interval_seconds
            or trigger_config.interval_minutes
            or trigger_config.interval_hours
            or trigger_config.interval_days
        )
        if not has_interval:
            raise HTTPException(status_code=422, detail="At least one interval parameter required for interval trigger")
    elif trigger_type == "one_time":
        if not trigger_config.start_date:
            raise HTTPException(status_code=422, detail="start_date required for one_time trigger")
    else:
        raise HTTPException(status_code=422, detail=f"Invalid trigger_type: {trigger_type}")


def _get_task_shares(task_id: str) -> list[str]:
    conn = _get_db()
    try:
        cursor = conn.execute(
            "SELECT target_workspace_id FROM task_shares WHERE task_id = ?",
            (task_id,),
        )
        return [row["target_workspace_id"] for row in cursor.fetchall()]
    finally:
        conn.close()


def _is_task_shared_to_workspace(task_id: str, workspace_id: str) -> bool:
    conn = _get_db()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM task_shares WHERE task_id = ? AND target_workspace_id = ?",
            (task_id, workspace_id),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def _task_response_from_row(row: sqlite3.Row) -> TaskResponse:
    task = _row_to_task(row)
    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
        workspace_id=task["workspace_id"],
        visibility=task["visibility"],
        name=task["name"],
        description=task["description"],
        trigger_type=task["trigger_type"],
        trigger_config=task["trigger_config"],
        prompt_template=task["prompt_template"],
        model_name=task["model_name"],
        skill_names=task["skill_names"],
        notification_config=task["notification_config"],
        output_config=task["output_config"],
        status=task["status"],
        next_run_at=_calculate_next_run(task["trigger_type"], task["trigger_config"]),
        last_run_at=task["last_run_at"],
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
        shared_to=_get_task_shares(task["id"]),
        thread_id=task.get("thread_id"),
    )


async def _create_thread_for_task(request: Request, task_id: str, user) -> str | None:
    try:
        from langgraph.checkpoint.base import empty_checkpoint

        from app.gateway.deps import get_checkpointer, get_store
        from app.gateway.ownership import attach_owner_metadata
        from app.gateway.routers.threads import _store_upsert

        store = get_store(request)
        checkpointer = get_checkpointer(request)
        if store is None or checkpointer is None:
            logger.warning("Store or checkpointer not available, cannot create thread for task")
            return None

        thread_id = str(uuid.uuid4())
        now = time.time()
        metadata = attach_owner_metadata({"task_id": task_id, "visibility": "workspace"}, user)

        if store is not None:
            await _store_upsert(store, thread_id, metadata=metadata)

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        ckpt_metadata = {
            "step": -1,
            "source": "input",
            "writes": None,
            "parents": {},
            **metadata,
            "created_at": now,
        }
        await checkpointer.aput(config, empty_checkpoint(), ckpt_metadata, {})

        try:
            from langgraph_sdk.client import get_client
            lg_client = get_client(url="http://langgraph:2024")
            await lg_client.threads.create(thread_id=thread_id, metadata=metadata, if_exists=None)
        except Exception:
            logger.debug("Failed to sync thread to LangGraph Server (non-critical)")

        logger.info(f"Thread created for task {task_id}: {thread_id}")
        return thread_id
    except Exception:
        logger.exception(f"Failed to create thread for task {task_id}")
        return None


@router.post("", response_model=TaskResponse)
async def create_task(body: TaskCreateRequest, request: Request) -> TaskResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()
    _validate_trigger_config(body.trigger_type, body.trigger_config)

    task_id = str(uuid.uuid4())
    now = time.time()

    thread_id = await _create_thread_for_task(request, task_id, user)

    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO tasks (id, user_id, workspace_id, visibility, name, description,
                trigger_type, trigger_config, prompt_template, model_name, skill_names,
                notification_config, output_config, status, thread_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                user.id,
                workspace_id,
                "private",
                body.name,
                body.description,
                body.trigger_type,
                json.dumps(body.trigger_config.model_dump()),
                body.prompt_template,
                body.model_name,
                json.dumps(body.skill_names),
                json.dumps(body.notification_config.model_dump()),
                json.dumps(body.output_config.model_dump()),
                "active",
                thread_id,
                now,
                now,
            ),
        )
        conn.commit()

        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        logger.info(f"Task created: {task_id} by user {user.id} in workspace {workspace_id}")
        return _task_response_from_row(row)
    finally:
        conn.close()


@router.get("", response_model=list[TaskResponse])
async def list_tasks(request: Request) -> list[TaskResponse]:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute(
            """SELECT * FROM tasks WHERE user_id = ? OR id IN
                (SELECT task_id FROM task_shares WHERE target_workspace_id = ?)
            ORDER BY updated_at DESC""",
            (user.id, workspace_id),
        )
        rows = cursor.fetchall()
        return [_task_response_from_row(row) for row in rows]
    finally:
        conn.close()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = _row_to_task(row)
        if task["user_id"] != user.id:
            if not (workspace_id and _is_task_shared_to_workspace(task_id, workspace_id)):
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return _task_response_from_row(row)
    finally:
        conn.close()


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, body: TaskUpdateRequest, request: Request) -> TaskResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        trigger_type = body.trigger_type or row["trigger_type"]
        trigger_config = body.trigger_config or TriggerConfig(**json.loads(row["trigger_config"]))
        if body.trigger_type is not None or body.trigger_config is not None:
            _validate_trigger_config(trigger_type, trigger_config)

        now = time.time()
        updates = []
        params = []

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)
        if body.description is not None:
            updates.append("description = ?")
            params.append(body.description)
        if body.trigger_type is not None:
            updates.append("trigger_type = ?")
            params.append(body.trigger_type)
        if body.trigger_config is not None:
            updates.append("trigger_config = ?")
            params.append(json.dumps(body.trigger_config.model_dump()))
        if body.prompt_template is not None:
            updates.append("prompt_template = ?")
            params.append(body.prompt_template)
        if body.model_name is not None:
            updates.append("model_name = ?")
            params.append(body.model_name)
        if body.skill_names is not None:
            updates.append("skill_names = ?")
            params.append(json.dumps(body.skill_names))
        if body.notification_config is not None:
            updates.append("notification_config = ?")
            params.append(json.dumps(body.notification_config.model_dump()))
        if body.output_config is not None:
            updates.append("output_config = ?")
            params.append(json.dumps(body.output_config.model_dump()))
        if body.status is not None:
            updates.append("status = ?")
            params.append(body.status)

        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)

        conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        logger.info(f"Task updated: {task_id}")
        return _task_response_from_row(row)
    finally:
        conn.close()


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        conn.execute("DELETE FROM task_shares WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM task_executions WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

        logger.info(f"Task deleted: {task_id}")
        return {"success": True, "message": f"Task {task_id} deleted"}
    finally:
        conn.close()


@router.post("/{task_id}/share", response_model=ShareResponse)
async def share_task(task_id: str, body: TaskShareRequest, request: Request) -> ShareResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        cursor = conn.execute(
            "SELECT 1 FROM task_shares WHERE task_id = ? AND target_workspace_id = ?",
            (task_id, body.target_workspace_id),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Already shared to this workspace")

        share_id = str(uuid.uuid4())
        now = time.time()

        conn.execute(
            """INSERT INTO task_shares (id, task_id, target_workspace_id, permission, shared_by, shared_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (share_id, task_id, body.target_workspace_id, body.permission, user.id, now),
        )
        conn.commit()

        logger.info(f"Task {task_id} shared to workspace {body.target_workspace_id}")
        return ShareResponse(
            id=share_id,
            task_id=task_id,
            target_workspace_id=body.target_workspace_id,
            permission=body.permission,
            shared_by=user.id,
            shared_at=str(now),
        )
    finally:
        conn.close()


@router.delete("/{task_id}/share/{share_id}")
async def unshare_task(task_id: str, share_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        cursor = conn.execute(
            "SELECT * FROM task_shares WHERE id = ? AND task_id = ?",
            (share_id, task_id),
        )
        share = cursor.fetchone()
        if not share:
            raise HTTPException(status_code=404, detail=f"Share {share_id} not found")

        conn.execute("DELETE FROM task_shares WHERE id = ?", (share_id,))
        conn.commit()

        logger.info(f"Task {task_id} unshared (share {share_id})")
        return {"success": True, "message": f"Share {share_id} removed"}
    finally:
        conn.close()


@router.post("/{task_id}/run", response_model=TaskExecutionResponse)
async def run_task_now(task_id: str, request: Request) -> TaskExecutionResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = _row_to_task(row)
        execution_id = str(uuid.uuid4())
        now = time.time()

        conn.execute(
            """INSERT INTO task_executions (id, task_id, status, started_at)
            VALUES (?, ?, ?, ?)""",
            (execution_id, task_id, "running", now),
        )
        conn.commit()

        thread_id = task.get("thread_id")
        if not thread_id:
            thread_id = await _create_thread_for_task(request, task_id, user)
            if thread_id:
                conn.execute("UPDATE tasks SET thread_id = ? WHERE id = ?", (thread_id, task_id))
                conn.commit()

        if not thread_id:
            raise HTTPException(status_code=500, detail="Failed to create or get thread for task execution")

        try:
            result_data = await _execute_task_in_thread(
                request=request,
                thread_id=thread_id,
                prompt_template=task["prompt_template"],
                model_name=task.get("model_name"),
                skill_names=task.get("skill_names", []),
            )

            completed_at = time.time()
            result_summary = result_data.get("result_summary", "")
            error_message = result_data.get("error_message")
            status = "success" if not error_message else "failed"

            conn.execute(
                """UPDATE task_executions
                SET status = ?, completed_at = ?, result_summary = ?, error_message = ?, thread_id = ?
                WHERE id = ?""",
                (status, completed_at, result_summary, error_message, thread_id, execution_id),
            )
            conn.execute("UPDATE tasks SET last_run_at = ? WHERE id = ?", (completed_at, task_id))
            conn.commit()

            logger.info(f"Task {task_id} execution {execution_id} completed with status {status}")
            return TaskExecutionResponse(
                id=execution_id,
                task_id=task_id,
                thread_id=thread_id,
                status=status,
                started_at=str(now),
                completed_at=str(completed_at),
                result_summary=result_summary,
                error_message=error_message,
                token_used=0,
            )

        except Exception as exc:
            completed_at = time.time()
            error_msg = str(exc)
            logger.exception(f"Task {task_id} execution {execution_id} failed")

            conn.execute(
                """UPDATE task_executions
                SET status = ?, completed_at = ?, error_message = ?, thread_id = ?
                WHERE id = ?""",
                ("failed", completed_at, error_msg, thread_id, execution_id),
            )
            conn.commit()

            return TaskExecutionResponse(
                id=execution_id,
                task_id=task_id,
                thread_id=thread_id,
                status="failed",
                started_at=str(now),
                completed_at=str(completed_at),
                result_summary=None,
                error_message=error_msg,
                token_used=0,
            )

    finally:
        conn.close()


async def _execute_task_in_thread(
    request: Request,
    thread_id: str,
    prompt_template: str,
    model_name: str | None,
    skill_names: list[str],
) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage

    from app.gateway.deps import get_checkpointer, get_run_manager, get_store
    from app.gateway.ownership import attach_owner_metadata
    from app.gateway.services import build_run_config, normalize_input, resolve_agent_factory
    from deerflow.runtime import run_agent
    from deerflow.runtime.runs.schemas import DisconnectMode
    from deerflow.runtime.stream_bridge.memory import MemoryStreamBridge

    run_mgr = get_run_manager(request)
    checkpointer = get_checkpointer(request)
    store = get_store(request)

    metadata = attach_owner_metadata({}, request.state.current_user)

    graph_input = normalize_input({"messages": [HumanMessage(content=prompt_template)]})

    context: dict[str, Any] = {}
    if model_name:
        context["model_name"] = model_name

    config = build_run_config(
        thread_id=thread_id,
        request_config=None,
        metadata=metadata,
        assistant_id=None,
    )
    config.setdefault("metadata", {}).update({"user_id": request.state.current_user.id})

    if context:
        _CONTEXT_CONFIGURABLE_KEYS = {
            "model_name",
            "mode",
            "thinking_enabled",
            "reasoning_effort",
            "is_plan_mode",
            "subagent_enabled",
            "max_concurrent_subagents",
        }
        configurable = config.setdefault("configurable", {})
        for key in _CONTEXT_CONFIGURABLE_KEYS:
            if key in context:
                configurable.setdefault(key, context[key])

    agent_factory = resolve_agent_factory(None)

    bridge = MemoryStreamBridge()

    record = await run_mgr.create_or_reject(
        thread_id,
        None,
        on_disconnect=DisconnectMode.cancel,
        metadata=metadata,
        kwargs={"input": graph_input, "config": config},
        multitask_strategy="reject",
    )

    if store is not None:
        try:
            from app.gateway.routers.threads import _store_upsert
            await _store_upsert(store, thread_id, metadata=metadata)
        except Exception:
            pass

    task = asyncio.create_task(
        run_agent(
            bridge,
            run_mgr,
            record,
            checkpointer=checkpointer,
            store=store,
            agent_factory=agent_factory,
            graph_input=graph_input,
            config=config,
            stream_modes=["values"],
            stream_subgraphs=False,
            interrupt_before=None,
            interrupt_after=None,
        )
    )

    try:
        await asyncio.wait({task})
    except asyncio.CancelledError:
        pass

    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple is not None:
            checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}
            channel_values = checkpoint.get("channel_values", {})
            messages = channel_values.get("messages", [])
            ai_responses = [m.content for m in messages if hasattr(m, "type") and m.type == "ai"]
            if ai_responses:
                return {"result_summary": ai_responses[-1], "error_message": None}
    except Exception:
        pass

    try:
        from langgraph_sdk.client import get_client
        lg_client = get_client(url="http://langgraph:2024")
        await lg_client.threads.update(thread_id, metadata={"task_executed": str(time.time())})
    except Exception:
        logger.debug("Failed to sync thread after task execution (non-critical)")

    return {"result_summary": "Task completed", "error_message": None}


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        now = time.time()
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("paused", now, task_id))
        conn.commit()

        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        logger.info(f"Task paused: {task_id}")
        return _task_response_from_row(row)
    finally:
        conn.close()


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        now = time.time()
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("active", now, task_id))
        conn.commit()

        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        logger.info(f"Task resumed: {task_id}")
        return _task_response_from_row(row)
    finally:
        conn.close()


@router.get("/{task_id}/executions", response_model=list[TaskExecutionResponse])
async def list_task_executions(task_id: str, request: Request) -> list[TaskExecutionResponse]:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row or row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        cursor = conn.execute(
            "SELECT * FROM task_executions WHERE task_id = ? ORDER BY started_at DESC",
            (task_id,),
        )
        executions = []
        for exec_row in cursor.fetchall():
            executions.append(
                TaskExecutionResponse(
                    id=exec_row["id"],
                    task_id=exec_row["task_id"],
                    thread_id=exec_row["thread_id"],
                    status=exec_row["status"],
                    started_at=str(exec_row["started_at"]) if exec_row["started_at"] else None,
                    completed_at=str(exec_row["completed_at"]) if exec_row["completed_at"] else None,
                    result_summary=exec_row["result_summary"],
                    error_message=exec_row["error_message"],
                    token_used=exec_row["token_used"],
                )
            )
        return executions
    finally:
        conn.close()
