"""Scheduler service for managing scheduled tasks using APScheduler."""

from __future__ import annotations

import logging
from typing import Any, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

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
        interval_seconds = (
            trigger_config.get("interval_seconds")
            or (trigger_config.get("interval_minutes", 0) * 60)
            or (trigger_config.get("interval_hours", 0) * 3600)
            or (trigger_config.get("interval_days", 0) * 86400)
            or 60
        )
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
