"""Unit tests for full checkpoint rollback on abort (worker.py Phase 2)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from deerflow.runtime.runs.manager import RunManager, RunRecord
from deerflow.runtime.runs.schemas import RunStatus
from deerflow.runtime.runs.worker import run_agent
from deerflow.runtime.stream_bridge.memory import MemoryStreamBridge

try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph.state import StateGraph
except ImportError:  # pragma: no cover
    pytest.skip("langgraph is a required dependency", allow_module_level=True)


def _compile_graph(saver: Any, *, tag: str = "visited"):
    """A trivial compiled LangGraph over a checkpointer."""
    graph = StateGraph(dict)
    graph.add_node("n", lambda s: {**s, tag: True})
    graph.set_entry_point("n")
    return graph.compile(checkpointer=saver)


async def _seed_checkpoint(saver: InMemorySaver, thread_id: str) -> None:
    """Write one real checkpoint into *saver* for *thread_id*."""
    compiled = _compile_graph(saver)
    await compiled.ainvoke({}, {"configurable": {"thread_id": thread_id}})


async def _root_state(saver: InMemorySaver, thread_id: str) -> dict:
    """Return the thread's current root channel values (or {} if absent)."""
    ckpt = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
    if ckpt is None or ckpt.checkpoint is None:
        return {}
    return ckpt.checkpoint.get("channel_values", {}).get("__root__", {})


def _new_bridge() -> MemoryStreamBridge:
    """A real in-memory bridge (implements every StreamBridge method)."""
    return MemoryStreamBridge()


def _build_advancing_abort_factory(
    record: RunRecord,
    saver: InMemorySaver,
    thread_id: str,
) -> Any:
    """A factory returning an agent whose astream advances the thread then aborts.

    Simulates a run that (a) writes newer checkpoints past the pre-run tip, then
    (b) signals abort so the worker's streaming loop breaks into the abort path.
    """

    async def _advance_then_abort(graph_input: Any, *, config: Any) -> AsyncIterator[Any]:
        # Write a NEWER checkpoint that differs from the pre-run state, so we
        # can prove rollback removes it.
        compiled = _compile_graph(saver, tag="advanced")
        await compiled.ainvoke({}, {"configurable": {"thread_id": thread_id}})
        record.abort_event.set()
        yield 0

    class _Agent:
        checkpointer: Any = saver
        store: Any = None
        interrupt_before_nodes: Any = None
        interrupt_after_nodes: Any = None

        async def astream(
            self,
            graph_input: Any,
            config: Any = None,
            *,
            stream_mode: Any = None,
            subgraphs: bool = False,
        ) -> AsyncIterator[Any]:
            async for chunk in _advance_then_abort(graph_input, config=stream_mode):
                yield chunk

    def factory(config: Any) -> Any:
        return _Agent()

    return factory


async def test_rollback_restores_pre_run_checkpoint_after_run_advanced() -> None:
    """abort-action=rollback rewinds the thread to the pre-run checkpoint."""
    saver = InMemorySaver()
    thread_id = "t-rollback"
    await _seed_checkpoint(saver, thread_id)
    pre_root = await _root_state(saver, thread_id)
    assert pre_root == {"visited": True}

    mgr = RunManager()
    record = await mgr.create(thread_id, on_disconnect="cancel")
    record.abort_action = "rollback"

    await run_agent(
        _new_bridge(),
        mgr,
        record,
        checkpointer=saver,
        store=None,
        agent_factory=_build_advancing_abort_factory(record, saver, thread_id),
        graph_input={},
        config={"configurable": {"thread_id": thread_id}},
        stream_modes=["values"],
    )

    # Status + message reflect the rollback.
    assert record.status == RunStatus.error
    assert record.error == "Rolled back by user"

    # The run wrote a NEWER state (advanced=True) past pre_run while streaming.
    # A real rollback rewinds the thread so that newer state is gone and the
    # root channel values are restored to the pre-run snapshot.
    assert await _root_state(saver, thread_id) == pre_root
    assert await _root_state(saver, thread_id) == {"visited": True}


async def test_rollback_still_errors_when_no_pre_run_checkpoint() -> None:
    """Rollback with no pre-run checkpoint still records error (no crash)."""
    saver = InMemorySaver()
    thread_id = "t-no-pre"

    mgr = RunManager()
    record = await mgr.create(thread_id, on_disconnect="cancel")
    record.abort_action = "rollback"

    await run_agent(
        _new_bridge(),
        mgr,
        record,
        checkpointer=saver,
        store=None,
        agent_factory=_build_abort_noop_factory(record),
        graph_input={},
        config={"configurable": {"thread_id": thread_id}},
        stream_modes=["values"],
    )

    assert record.status == RunStatus.error
    assert record.error == "Rolled back by user"


def _build_abort_noop_factory(record: RunRecord) -> Any:
    """An agent that aborts immediately WITHOUT writing any checkpoint."""

    class _Agent:
        checkpointer: Any = None
        store: Any = None
        interrupt_before_nodes: Any = None
        interrupt_after_nodes: Any = None

        async def astream(
            self,
            graph_input: Any,
            config: Any = None,
            *,
            stream_mode: Any = None,
            subgraphs: bool = False,
        ) -> AsyncIterator[Any]:
            record.abort_event.set()
            yield 0

    def factory(config: Any) -> Any:
        return _Agent()

    return factory