"""Scheduled Tasks API - CRUD and execution endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TriggerConfig(BaseModel):
    """Configuration for task triggers."""

    cron: str | None = Field(default=None, description="Cron expression (e.g., '0 9 * * *')")
    interval_seconds: int | None = Field(default=None, description="Interval in seconds")
    interval_minutes: int | None = Field(default=None, description="Interval in minutes")
    interval_hours: int | None = Field(default=None, description="Interval in hours")
    interval_days: int | None = Field(default=None, description="Interval in days")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone for cron")
    start_date: str | None = Field(default=None, description="ISO datetime to start scheduling")
    end_date: str | None = Field(default=None, description="ISO datetime to end scheduling")


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


class TaskResponse(BaseModel):
    id: str
    user_id: str
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


_tasks_store: dict[str, dict] = {}
_executions_store: dict[str, dict] = {}


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
                next_run = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=interval_seconds)
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


@router.post("", response_model=TaskResponse)
async def create_task(body: TaskCreateRequest, request: Request) -> TaskResponse:
    user = require_user(request)
    _validate_trigger_config(body.trigger_type, body.trigger_config)

    task_id = str(uuid.uuid4())
    now = time.time()

    task = {
        "id": task_id,
        "user_id": user.id,
        "name": body.name,
        "description": body.description,
        "trigger_type": body.trigger_type,
        "trigger_config": body.trigger_config.model_dump(),
        "prompt_template": body.prompt_template,
        "model_name": body.model_name,
        "skill_names": body.skill_names,
        "notification_config": body.notification_config.model_dump(),
        "output_config": body.output_config.model_dump(),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    _tasks_store[task_id] = task
    logger.info(f"Task created: {task_id} by user {user.id}")

    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
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
        last_run_at=None,
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(request: Request) -> list[TaskResponse]:
    user = require_user(request)
    tasks = []
    for task in _tasks_store.values():
        if task["user_id"] == user.id:
            tasks.append(
                TaskResponse(
                    id=task["id"],
                    user_id=task["user_id"],
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
                    last_run_at=task.get("last_run_at"),
                    created_at=str(task["created_at"]),
                    updated_at=str(task["updated_at"]),
                )
            )
    tasks.sort(key=lambda t: t.updated_at, reverse=True)
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
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
        last_run_at=task.get("last_run_at"),
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, body: TaskUpdateRequest, request: Request) -> TaskResponse:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if body.name is not None:
        task["name"] = body.name
    if body.description is not None:
        task["description"] = body.description
    if body.trigger_type is not None:
        task["trigger_type"] = body.trigger_type
    if body.trigger_config is not None:
        task["trigger_config"] = body.trigger_config.model_dump()
    if body.prompt_template is not None:
        task["prompt_template"] = body.prompt_template
    if body.model_name is not None:
        task["model_name"] = body.model_name
    if body.skill_names is not None:
        task["skill_names"] = body.skill_names
    if body.notification_config is not None:
        task["notification_config"] = body.notification_config.model_dump()
    if body.output_config is not None:
        task["output_config"] = body.output_config.model_dump()
    if body.status is not None:
        task["status"] = body.status
    task["updated_at"] = time.time()

    logger.info(f"Task updated: {task_id}")
    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
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
        last_run_at=task.get("last_run_at"),
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
    )


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request) -> dict:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    del _tasks_store[task_id]
    logger.info(f"Task deleted: {task_id}")
    return {"success": True, "message": f"Task {task_id} deleted"}


@router.post("/{task_id}/run", response_model=TaskExecutionResponse)
async def run_task_now(task_id: str, request: Request) -> TaskExecutionResponse:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    execution_id = str(uuid.uuid4())
    now = time.time()
    execution = {
        "id": execution_id,
        "task_id": task_id,
        "thread_id": None,
        "status": "pending",
        "started_at": now,
        "completed_at": None,
        "result_summary": None,
        "error_message": None,
        "token_used": 0,
    }
    _executions_store[execution_id] = execution
    logger.info(f"Task run triggered: {task_id} execution {execution_id}")
    execution["status"] = "running"

    return TaskExecutionResponse(
        id=execution["id"],
        task_id=execution["task_id"],
        thread_id=execution["thread_id"],
        status=execution["status"],
        started_at=str(execution["started_at"]) if execution["started_at"] else None,
        completed_at=str(execution["completed_at"]) if execution["completed_at"] else None,
        result_summary=execution["result_summary"],
        error_message=execution["error_message"],
        token_used=execution["token_used"],
    )


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task["status"] = "paused"
    task["updated_at"] = time.time()
    logger.info(f"Task paused: {task_id}")

    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
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
        next_run_at=None,
        last_run_at=task.get("last_run_at"),
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
    )


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(task_id: str, request: Request) -> TaskResponse:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task["status"] = "active"
    task["updated_at"] = time.time()
    logger.info(f"Task resumed: {task_id}")

    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
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
        last_run_at=task.get("last_run_at"),
        created_at=str(task["created_at"]),
        updated_at=str(task["updated_at"]),
    )


@router.get("/{task_id}/executions", response_model=list[TaskExecutionResponse])
async def list_task_executions(task_id: str, request: Request) -> list[TaskExecutionResponse]:
    user = require_user(request)
    task = _tasks_store.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    executions = []
    for exec_record in _executions_store.values():
        if exec_record["task_id"] == task_id:
            executions.append(
                TaskExecutionResponse(
                    id=exec_record["id"],
                    task_id=exec_record["task_id"],
                    thread_id=exec_record["thread_id"],
                    status=exec_record["status"],
                    started_at=str(exec_record["started_at"]) if exec_record["started_at"] else None,
                    completed_at=str(exec_record["completed_at"]) if exec_record["completed_at"] else None,
                    result_summary=exec_record["result_summary"],
                    error_message=exec_record["error_message"],
                    token_used=exec_record["token_used"],
                )
            )
    executions.sort(key=lambda e: e.started_at or "", reverse=True)
    return executions
