"""Verify MemoryStorage.save() does not block the event loop.

Root cause of `BlockingError: os.mkdir` in LangGraph context: save()
calls os.mkdir() synchronously inside an async function, which LangGraph's
blockbuster library detects as a blocking call.

Fix: save() should be async and use asyncio.to_thread for the file I/O.

NOTE on plan drift: The original plan referenced `MICX_MEMORY_DIR` as
the env var to control memory location. The real env var used by
`deerflow.config.paths.Paths.base_dir` is `DEER_FLOW_HOME`. The test
has been adapted to use the real env var while preserving the original
intent.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest

from deerflow.agents.memory.storage import FileMemoryStorage


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Create a FileMemoryStorage rooted at a temp directory.

    Points `DEER_FLOW_HOME` at the pytest tmp_path so the storage's
    resolved memory_file lives entirely under tmp_path.
    """
    monkeypatch.setenv("DEER_FLOW_HOME", str(tmp_path))
    return FileMemoryStorage()


def test_save_is_coroutine(temp_storage):
    """Verify save() is async (returns coroutine)."""
    coro = temp_storage.save(
        {"facts": [], "user_context": {}, "history": {}},
        agent_name="test",
        user_id="user1",
    )
    # If save() is async, calling it returns a coroutine without executing
    assert inspect.iscoroutine(coro), (
        f"save() should return a coroutine (be async), but returned {type(coro).__name__}"
    )
    # Close the coroutine to avoid 'never awaited' warning
    coro.close()


@pytest.mark.asyncio
async def test_save_does_not_block_event_loop(temp_storage):
    """Verify save() uses asyncio.to_thread and doesn't block the loop."""
    # Schedule a coroutine that should run if save() is properly async
    ping_done = asyncio.Event()

    async def ping():
        await asyncio.sleep(0)  # yield to scheduler
        ping_done.set()

    # Start ping in background
    ping_task = asyncio.create_task(ping())

    # Call save (should be async and not block)
    result = await temp_storage.save(
        {"facts": [], "user_context": {}, "history": {}},
        agent_name="test",
        user_id="user1",
    )
    assert result is True

    # Ping should have completed during save (proving event loop wasn't blocked)
    assert ping_done.is_set()
    await ping_task


def test_sync_save_method_exists_for_thread_pool(temp_storage):
    """Verify _sync_save() exists as the underlying sync implementation."""
    # The fix splits save() into async wrapper + sync _sync_save()
    assert hasattr(temp_storage, "_sync_save"), (
        "MemoryStorage should have _sync_save() method for asyncio.to_thread wrapping"
    )

    result = temp_storage._sync_save(
        {"facts": [], "user_context": {}, "history": {}},
        agent_name="test",
        user_id="user1",
    )
    # _sync_save is sync (returns bool)
    assert isinstance(result, bool)