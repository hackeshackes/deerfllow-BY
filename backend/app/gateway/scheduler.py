"""Scheduler service for managing scheduled tasks using APScheduler."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_job_callbacks: dict[str, Callable] = {}


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def _create_trigger(trigger_type: str, trigger_config: dict) -> Any:
    if trigger_type == "cron":
        return CronTrigger(
            cron=trigger_config.get("cron", "0 9 * * *"),
            timezone=trigger_config.get("timezone", "Asia/Shanghai"),
        )
    elif trigger_type == "interval":
        interval_seconds = trigger_config.get("interval_seconds") or ((trigger_config.get("interval_minutes") or 0) * 60) or ((trigger_config.get("interval_hours") or 0) * 3600) or ((trigger_config.get("interval_days") or 0) * 86400) or 60
        return IntervalTrigger(seconds=interval_seconds, timezone=trigger_config.get("timezone", "Asia/Shanghai"))
    elif trigger_type == "one_time":
        start_date = trigger_config.get("start_date")
        return DateTrigger(run_date=start_date)
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")


def add_scheduled_job(
    task_id: str,
    trigger_type: str,
    trigger_config: dict,
    callback: Callable,
    name: str | None = None,
) -> str:
    scheduler = get_scheduler()
    trigger = _create_trigger(trigger_type, trigger_config)
    job_id = f"task_{task_id}"
    scheduler.add_job(
        callback,
        trigger=trigger,
        args=(task_id,),
        id=job_id,
        name=name or f"Scheduled task: {task_id}",
        replace_existing=True,
    )
    _job_callbacks[job_id] = callback
    logger.info(f"Added scheduled job: {job_id}")
    return job_id


def remove_scheduled_job(task_id: str) -> bool:
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    try:
        scheduler.remove_job(job_id)
        _job_callbacks.pop(job_id, None)
        logger.info(f"Removed scheduled job: {job_id}")
        return True
    except Exception:
        return False


def pause_scheduled_job(task_id: str) -> bool:
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    try:
        scheduler.pause_job(job_id)
        logger.info(f"Paused scheduled job: {job_id}")
        return True
    except Exception:
        return False


def resume_scheduled_job(task_id: str) -> bool:
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    try:
        scheduler.resume_job(job_id)
        logger.info(f"Resumed scheduled job: {job_id}")
        return True
    except Exception:
        return False


def get_next_run_time(task_id: str) -> str | None:
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    job = scheduler.get_job(job_id)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


def trigger_job_now(task_id: str) -> bool:
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    try:
        scheduler.modify_job(job_id, next_run_time=None)
        scheduler.run_job(job_id)
        logger.info(f"Triggered job immediately: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to trigger job {job_id}: {e}")
        return False


_SCHEDULER_INTERNAL_KEY = "scheduler-internal-key-2026"


async def _execute_scheduled_task(task_id: str) -> None:
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://gateway:8001/api/tasks/{task_id}/run",
                headers={"X-Scheduler-Key": _SCHEDULER_INTERNAL_KEY},
                timeout=300.0,
            )
            if response.status_code == 200:
                logger.info(f"Scheduled task {task_id} executed successfully")
            else:
                logger.error(f"Scheduled task {task_id} failed with status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to execute scheduled task {task_id}: {e}")


def _run_scheduled_task_sync(task_id: str) -> None:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_execute_scheduled_task(task_id))


async def load_scheduled_tasks_from_db() -> None:
    db_path = Path(__file__).parent / "data" / "tasks.db"
    if not db_path.exists():
        logger.info("No tasks.db found, skipping task loading")
        return
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, name, trigger_type, trigger_config FROM tasks WHERE status = 'active'")
    for row in cursor.fetchall():
        task_id = row["id"]
        name = row["name"]
        trigger_type = row["trigger_type"]
        trigger_config = json.loads(row["trigger_config"])
        add_scheduled_job(
            task_id=task_id,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            callback=_run_scheduled_task_sync,
            name=name,
        )
    conn.close()
    logger.info("Loaded scheduled tasks from database")
