"""Verify MemoryUpdateQueue does NOT use asyncio.run() per update in a background thread.

Root cause of `Event loop is closed` errors: queue.py:_process_queue() runs
in threading.Timer and calls asyncio.run() once per conversation context.
This creates and destroys a new event loop each time, breaking httpx/openai
async client state (which caches event loop references).

Fix: schedule processing via asyncio.create_task() on a long-lived event
loop. asyncio.run() should be called at most once (only for bootstrap when
called from sync code without a running loop). The tests below verify the
queue does not call asyncio.run() per queued context.

NOTE on plan drift: The original plan referred to `MemoryQueue` and
`MemoryContext` classes, which do not exist in this codebase. The actual
classes are `MemoryUpdateQueue` (queue.py) and `ConversationContext`
(queue.py). The test has been adapted to use the real class names while
preserving the original intent.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from deerflow.agents.memory.queue import ConversationContext, MemoryUpdateQueue
from deerflow.config.memory_config import MemoryConfig


def _memory_config(**overrides: object) -> MemoryConfig:
    config = MemoryConfig()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _make_context(thread_id: str = "test-thread") -> ConversationContext:
    """Create a minimal ConversationContext for testing."""
    return ConversationContext(
        thread_id=thread_id,
        messages=[],
        agent_name="test-agent",
        user_id="test-user",
    )


def test_queue_does_not_call_asyncio_run_per_update():
    """Verify _process_queue does NOT use asyncio.run() per call.

    This test fails on the buggy code (where asyncio.run is called once
    per conversation context inside the background timer thread).
    """
    queue = MemoryUpdateQueue()

    # Pre-populate queue; bypass the timer setup so flush() runs synchronously
    queue._queue = [_make_context("t1"), _make_context("t2")]

    with patch("deerflow.agents.memory.queue.asyncio.run") as mock_run:
        # Trigger processing via flush (cancels timer and calls _process_queue directly)
        queue.flush()

        # The buggy code would call asyncio.run() twice (once per context).
        # The fixed code should call asyncio.run() at most once (one-time loop bootstrap)
        # or zero times (pure async scheduling with no sync entry point).
        assert mock_run.call_count <= 1, (
            f"asyncio.run() called {mock_run.call_count} times; "
            f"expected ≤ 1 (one-time loop bootstrap)"
        )


def test_queue_processes_multiple_contexts_in_single_event_loop_pass():
    """Verify queue processes all queued contexts in a single event loop pass.

    Smoke test: pre-populate 3 contexts, call flush, verify no more than
    one event loop is created during processing.
    """
    queue = MemoryUpdateQueue()
    contexts = [_make_context(f"t{i}") for i in range(3)]
    queue._queue = list(contexts)

    loops_created: list[int] = []

    real_asyncio_run = asyncio.run

    def tracking_run(coro):
        loop = asyncio.new_event_loop()
        loops_created.append(id(loop))
        return real_asyncio_run(coro)

    # Patch the MemoryUpdater so we don't actually try to update memory.
    class FakeUpdater:
        async def update_memory(self, **_: object) -> bool:
            return True

    with (
        patch("deerflow.agents.memory.queue.asyncio.run", side_effect=tracking_run),
        patch("deerflow.agents.memory.updater.MemoryUpdater", return_value=FakeUpdater()),
    ):
        queue.flush()

    # Should only create 1 event loop total (or 0 if fully sync).
    assert len(loops_created) <= 1, (
        f"Created {len(loops_created)} event loops; expected ≤ 1. "
        f"Loop IDs: {loops_created}"
    )


def test_add_triggers_timer_with_configured_debounce():
    """Verify add() schedules processing via the debounce timer.

    This is a sanity check that the queue uses the threading.Timer + asyncio.run
    pipeline the plan is targeting; the failure mode is the per-update asyncio.run
    inside _process_queue, which the previous two tests cover.
    """
    queue = MemoryUpdateQueue()

    with patch.object(queue, "_reset_timer") as mock_reset:
        with patch(
            "deerflow.agents.memory.queue.get_memory_config",
            return_value=_memory_config(enabled=True),
        ):
            queue.add(thread_id="t-1", messages=["hello"])

    # _reset_timer was called → debounce timer is the scheduling path.
    mock_reset.assert_called_once()
    assert queue.pending_count == 1