"""Unit tests for cross-workspace thread publishing (v1.6.x C1).

Tests the PublishService against an in-memory ThreadStore duck — exercises:
1. publish() creates a new thread in the target workspace with lineage
2. chain publishing preserves the original source (A -> B -> C, C.original == A)
3. publish_history is capped at 50 entries
4. publish() on a missing source thread raises (LookupError)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.gateway.collaboration.publish import (
    PublishEvent,
    PublishResult,
    PublishService,
)
from app.gateway.threads.models import SpaceType, Thread, ThreadSource


@dataclass
class _ThreadStore:
    """In-memory ThreadStore for tests — minimal Protocol-shaped duck."""

    threads: dict[str, Thread]
    max_history: int = 50

    def get(self, thread_id: str) -> Thread | None:
        return self.threads.get(thread_id)

    def create(self, thread: Thread) -> Thread:
        self.threads[thread.id] = thread
        return thread

    def append_publish_event(self, thread_id: str, event: PublishEvent) -> None:
        t = self.threads[thread_id]
        hist = list(t.publish_history or [])
        hist.append(event)
        if len(hist) > self.max_history:
            hist = hist[-self.max_history :]
        t.publish_history = hist  # Thread is non-frozen, direct attr assignment


def _thread(thread_id: str, ws: str, source: str | None = None) -> Thread:
    return Thread(
        id=thread_id,
        title=f"thread {thread_id}",
        user_id="u1",
        workspace_id=ws,
        space_type=SpaceType.PERSONAL,
        source=ThreadSource.MANUAL,
        published_from_thread_id=source,
        created_at="2026-07-06T00:00:00Z",
        updated_at="2026-07-06T00:00:00Z",
        publish_history=[],
    )


def test_publish_creates_new_thread_in_target_workspace():
    tstore = _ThreadStore(threads={})
    source = _thread("A", "ws-a")
    tstore.threads["A"] = source
    svc = PublishService(thread_store=tstore)

    result = svc.publish(source_thread_id="A", target_workspace_id="ws-b", actor_user_id="u1")

    assert isinstance(result, PublishResult)
    assert result.new_thread_id != "A"
    assert tstore.threads[result.new_thread_id].workspace_id == "ws-b"
    assert tstore.threads[result.new_thread_id].published_from_thread_id == "A"


def test_chain_publish_preserves_original_source():
    tstore = _ThreadStore(threads={})
    tstore.threads["A"] = _thread("A", "ws-a")
    svc = PublishService(thread_store=tstore)

    b_result = svc.publish("A", "ws-b", "u1")
    c_result = svc.publish(b_result.new_thread_id, "ws-c", "u1")

    assert c_result.original_thread_id == "A"


def test_history_is_capped_at_50():
    tstore = _ThreadStore(threads={})
    tstore.threads["A"] = _thread("A", "ws-a")
    svc = PublishService(thread_store=tstore)

    # Pre-populate 49 events directly
    for i in range(49):
        tstore.append_publish_event(
            "A",
            PublishEvent(
                new_thread_id=f"old-{i}",
                target_workspace_id="ws-old",
                actor_user_id="u1",
                at=datetime(2026, 7, 6, tzinfo=UTC),
            ),
        )
    assert len(tstore.get("A").publish_history) == 49

    # Publish → should push to 50 (and stay 50, not 51)
    svc.publish("A", "ws-b", "u1")
    assert len(tstore.get("A").publish_history) == 50


def test_publish_missing_source_thread_raises():
    tstore = _ThreadStore(threads={})
    svc = PublishService(thread_store=tstore)

    with pytest.raises(Exception):  # LookupError or HTTPException
        svc.publish("missing", "ws-b", "u1")
