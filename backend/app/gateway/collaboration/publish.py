"""PublishService — cross-workspace thread publishing (v1.6.x B2).

Publishes a source thread into a target workspace by creating a brand-new
thread record (under a fresh UUID) that copies the source's lineage via the
``metadata.published_from_thread_id`` anchor, and appends an audit event to
the source's ``metadata.publish_history``.

Persistence is hidden behind a duck-typed ``StoreLike`` Protocol that matches
the langgraph Store API used elsewhere in the gateway (``aget`` / ``aput``
returning / accepting dicts, namespaced via ``THREADS_NS``). This keeps the
service unit-testable with an in-memory fake and integrable with the real
project Store via ``get_store(request)``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol


PUBLISH_HISTORY_MAX = 50
"""Maximum number of publish events kept per source thread."""


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


class StoreLike(Protocol):
    """Subset of langgraph Store used by PublishService.

    Real backend: ``get_store(request)`` returns a langgraph ``Store`` with
    ``async aget(ns, key) -> Item | None`` (Item has a ``.value`` dict) and
    ``async aput(ns, key, value: dict) -> None``. Thread records are stored
    under namespace ``THREADS_NS = ("threads",)``.
    """

    async def aget(self, ns: tuple[str, ...], key: str) -> Any | None:
        ...

    async def aput(self, ns: tuple[str, ...], key: str, value: dict) -> None:
        ...


class PublishService:
    """Async cross-workspace thread publisher.

    Persists both the new thread and the source's lineage via the Store.
    ``publish_history`` is capped at :data:`PUBLISH_HISTORY_MAX` at write time.
    """

    # Match the project namespace from ``app.gateway.routers.threads``.
    THREADS_NS: tuple[str, ...] = ("threads",)

    def __init__(
        self,
        store: StoreLike,
        threads_namespace: tuple[str, ...] = THREADS_NS,
    ) -> None:
        self._store = store
        self._ns = threads_namespace

    async def publish(
        self,
        source_thread_id: str,
        target_workspace_id: str,
        actor_user_id: str,
    ) -> PublishResult:
        """Publish ``source_thread_id`` into ``target_workspace_id``.

        Raises ``LookupError`` if the source thread does not exist.
        """
        source = await self._get_record(source_thread_id)
        if source is None:
            raise LookupError(f"thread {source_thread_id} not found")

        source_meta = dict(source.get("metadata") or {})
        original = source_meta.get("published_from_thread_id") or source_thread_id
        new_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        now_ts = now.timestamp()

        new_meta = {
            **source_meta,
            "published_from_thread_id": original,
            "publish_actor_user_id": actor_user_id,
            "publish_target_workspace_id": target_workspace_id,
        }

        new_record = {
            "thread_id": new_id,
            "status": "idle",
            "created_at": now_ts,
            "updated_at": now_ts,
            "metadata": new_meta,
            "values": None,
        }
        await self._put_record(new_id, new_record)

        # Append event to source's history with maxlen cap (write site).
        event = {
            "new_thread_id": new_id,
            "target_workspace_id": target_workspace_id,
            "actor_user_id": actor_user_id,
            "at": now_ts,
        }
        history = list(source_meta.get("publish_history") or [])
        history.append(event)
        if len(history) > PUBLISH_HISTORY_MAX:
            history = history[-PUBLISH_HISTORY_MAX:]
        source_meta["publish_history"] = history

        # Re-write the source record with the updated metadata in-place;
        # preserve thread_id, status, values.
        updated_source = dict(source)
        updated_source["metadata"] = source_meta
        updated_source["updated_at"] = now_ts
        await self._put_record(source_thread_id, updated_source)

        return PublishResult(
            new_thread_id=new_id,
            source_thread_id=source_thread_id,
            target_workspace_id=target_workspace_id,
            published_at=now,
            original_thread_id=original,
        )

    async def history(self, thread_id: str) -> list[PublishEvent]:
        """Return the publish history for a thread, or ``[]`` if thread is missing."""
        record = await self._get_record(thread_id)
        if record is None:
            return []
        events = list((record.get("metadata") or {}).get("publish_history") or [])
        out: list[PublishEvent] = []
        for e in events:
            try:
                out.append(
                    PublishEvent(
                        new_thread_id=e["new_thread_id"],
                        target_workspace_id=e["target_workspace_id"],
                        actor_user_id=e["actor_user_id"],
                        at=datetime.fromtimestamp(e["at"], tz=UTC),
                    )
                )
            except (KeyError, TypeError, ValueError):
                # Skip malformed entries rather than fail the whole history call.
                continue
        return out

    # ------------------------------------------------------------------
    # Store adapters — unwrap Item.value (real Store) / pass-through (fake)
    # ------------------------------------------------------------------

    async def _get_record(self, thread_id: str) -> dict | None:
        item = await self._store.aget(self._ns, thread_id)
        if item is None:
            return None
        # Real langgraph Store returns ``Item`` with ``.value`` (dict).
        value = getattr(item, "value", item)
        return value if isinstance(value, dict) else None

    async def _put_record(self, thread_id: str, record: dict) -> None:
        await self._store.aput(self._ns, thread_id, record)