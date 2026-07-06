"""PublishService — cross-workspace thread publishing (v1.6.x C1).

`PublishService` orchestrates the act of "publishing" a source thread into
a target workspace: a brand-new thread is created in the target workspace
that copies the source's lineage, and the source's ``publish_history`` is
appended with an audit event.

Thread persistence is hidden behind a duck-typed ``ThreadStore`` Protocol
so the service can be unit-tested with an in-memory store today and wired
into the project's real thread store later without changing call sites.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from app.gateway.threads.models import Thread, ThreadSource

PUBLISH_HISTORY_MAX = 50


@dataclass(frozen=True)
class PublishEvent:
    """One row of the source thread's publish audit log."""

    new_thread_id: str
    target_workspace_id: str
    actor_user_id: str
    at: datetime


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a successful publish."""

    new_thread_id: str
    source_thread_id: str
    target_workspace_id: str
    published_at: datetime
    original_thread_id: str


class ThreadStore(Protocol):
    """Subset of the project's thread store used by PublishService.

    Real integration: `app.gateway.routers.threads.create_thread` and the
    thread persistence layer; the v1.6.x integration phase will wire this.
    """

    def get(self, thread_id: str) -> Thread | None: ...
    def create(self, thread: Thread) -> Thread: ...
    def append_publish_event(self, thread_id: str, event: PublishEvent) -> None: ...


class PublishService:
    """Publish a thread into a target workspace, preserving lineage."""

    def __init__(self, thread_store: ThreadStore) -> None:
        self._threads = thread_store

    def publish(
        self,
        source_thread_id: str,
        target_workspace_id: str,
        actor_user_id: str,
    ) -> PublishResult:
        source = self._threads.get(source_thread_id)
        if source is None:
            raise LookupError(f"thread {source_thread_id} not found")

        original = source.published_from_thread_id or source.id
        new_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        new_thread = self._build_new_thread(source, new_id, target_workspace_id, actor_user_id, original, now)
        self._threads.create(new_thread)

        event = PublishEvent(
            new_thread_id=new_id,
            target_workspace_id=target_workspace_id,
            actor_user_id=actor_user_id,
            at=now,
        )
        self._threads.append_publish_event(source.id, event)

        return PublishResult(
            new_thread_id=new_id,
            source_thread_id=source.id,
            target_workspace_id=target_workspace_id,
            published_at=now,
            original_thread_id=original,
        )

    def history(self, thread_id: str) -> list[PublishEvent]:
        """Return the publish history for a thread, or [] if thread is missing."""
        t = self._threads.get(thread_id)
        if t is None:
            return []
        return list(getattr(t, "publish_history", []) or [])

    @staticmethod
    def _build_new_thread(
        source: Thread,
        new_id: str,
        target_workspace_id: str,
        actor_user_id: str,
        original: str,
        now: datetime,
    ) -> Thread:
        """Construct a new Thread in the target workspace, copying lineage."""
        return replace(
            source,
            id=new_id,
            workspace_id=target_workspace_id,
            user_id=actor_user_id,
            source=ThreadSource.MANUAL,
            published_from_thread_id=original,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            publish_history=[],
        )
