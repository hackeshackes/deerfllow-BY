"""Background agent execution.

Runs an agent graph inside an ``asyncio.Task``, publishing events to
a :class:`StreamBridge` as they are produced.

Uses ``graph.astream(stream_mode=[...])`` which gives correct full-state
snapshots for ``values`` mode, proper ``{node: writes}`` for ``updates``,
and ``(chunk, metadata)`` tuples for ``messages`` mode.

Note: ``events`` mode is not supported through the gateway — it requires
``graph.astream_events()`` which cannot simultaneously produce ``values``
snapshots.  The JS open-source LangGraph API server works around this via
internal checkpoint callbacks that are not exposed in the Python public API.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

from deerflow.runtime.serialization import serialize
from deerflow.runtime.stream_bridge import StreamBridge

from .manager import RunManager, RunRecord
from .schemas import RunStatus

logger = logging.getLogger(__name__)

# Valid stream_mode values for LangGraph's graph.astream()
_VALID_LG_MODES = {"values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"}


async def _rollback_checkpoint(
    checkpointer: Any,
    *,
    thread_id: str,
    pre_checkpoint_id: str | None,
) -> None:
    """Rewind *thread_id* to the checkpoint captured before a run started.

    Loads the pre-run checkpoint tuple and re-writes it as the thread's new tip
    under a fresh checkpoint id that sorts highest among the thread's stored
    checkpoints. The very next ``aget_tuple`` on the thread therefore returns
    the pre-run state, discarding any intermediate checkpoints the run wrote.
    The pre-run ``channel_versions`` are reused as the ``new_versions`` map, so
    ``aput`` re-blobs the pre-run channel values under their existing version
    keys.

    ``checkpointer`` may be ``None`` (no persistence) and ``pre_checkpoint_id``
    may be ``None`` (the thread had no prior checkpoint); both are no-ops.
    """
    if checkpointer is None or pre_checkpoint_id is None:
        return

    target = await checkpointer.aget_tuple(
        {"configurable": {"thread_id": thread_id, "checkpoint_id": pre_checkpoint_id}}
    )
    if target is None or getattr(target, "checkpoint", None) is None:
        return

    checkpoint = dict(target.checkpoint)
    # A fresh id that is *guaranteed* to sort strictly above any existing
    # checkpoint for the thread, so `aget_tuple` picks this one back up as the
    # new tip (rewinding to the pre-run state). uuid1's timestamp can stall on
    # the same clock tick, so we retry until strictly greater.
    new_id = await _new_tip_id(checkpointer, thread_id)
    checkpoint["id"] = new_id

    await checkpointer.aput(
        {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
        checkpoint,
        target.metadata,
        checkpoint.get("channel_versions") or {},
    )


async def _new_tip_id(checkpointer: Any, thread_id: str) -> str:
    """Return a checkpoint id that sorts strictly above the thread's current tip.

    Reads the existing tip id and, if a fresh ``uuid1()`` would not sort larger
    (same-millisecond generation), keeps drawing a carry-over id until it does.
    Guards against an absent tip by returning a plain fresh uuid1.
    """
    try:
        tip = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
    except Exception:  # pragma: no cover - belt-and-braces
        tip = None
    cur = tip.config.get("configurable", {}).get("checkpoint_id") if tip else None
    if cur is None:
        return str(uuid.uuid1())
    candidate = str(uuid.uuid1())
    # uuid1 is ordered by its timestamp; under the same clock tick the counter
    # still advances, but be defensive: keep drawing until it strictly sorts
    # above the current tip.
    while candidate <= cur:
        candidate = str(uuid.uuid1())
    return candidate


async def run_agent(
    bridge: StreamBridge,
    run_manager: RunManager,
    record: RunRecord,
    *,
    checkpointer: Any,
    store: Any | None = None,
    agent_factory: Any,
    graph_input: dict,
    config: dict,
    stream_modes: list[str] | None = None,
    stream_subgraphs: bool = False,
    interrupt_before: list[str] | Literal["*"] | None = None,
    interrupt_after: list[str] | Literal["*"] | None = None,
) -> None:
    """Execute an agent in the background, publishing events to *bridge*."""

    run_id = record.run_id
    thread_id = record.thread_id
    requested_modes: set[str] = set(stream_modes or ["values"])

    # Track whether "events" was requested but skipped
    if "events" in requested_modes:
        logger.info(
            "Run %s: 'events' stream_mode not supported in gateway (requires astream_events + checkpoint callbacks). Skipping.",
            run_id,
        )

    try:
        # 1. Mark running
        await run_manager.set_status(run_id, RunStatus.running)

        # Record pre-run checkpoint_id to support rollback (Phase 2).
        pre_run_checkpoint_id = None
        try:
            config_for_check = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
            ckpt_tuple = await checkpointer.aget_tuple(config_for_check)
            if ckpt_tuple is not None:
                pre_run_checkpoint_id = getattr(ckpt_tuple, "config", {}).get("configurable", {}).get("checkpoint_id")
        except Exception:
            logger.debug("Could not get pre-run checkpoint_id for run %s", run_id)

        # 2. Publish metadata — useStream needs both run_id AND thread_id
        await bridge.publish(
            run_id,
            "metadata",
            {
                "run_id": run_id,
                "thread_id": thread_id,
            },
        )

        # 3. Build the agent
        from langchain_core.runnables import RunnableConfig
        from langgraph.runtime import Runtime

        # Inject runtime context so middlewares can access thread_id
        # (langgraph-cli does this automatically; we must do it manually)
        runtime = Runtime(context={"thread_id": thread_id}, store=store)
        # If the caller already set a ``context`` key (LangGraph >= 0.6.0
        # prefers it over ``configurable`` for thread-level data), make
        # sure ``thread_id`` is available there too.
        if "context" in config and isinstance(config["context"], dict):
            config["context"].setdefault("thread_id", thread_id)
        config.setdefault("configurable", {})["__pregel_runtime"] = runtime

        runnable_config = RunnableConfig(**config)
        agent = agent_factory(config=runnable_config)

        # 4. Attach checkpointer and store
        if checkpointer is not None:
            agent.checkpointer = checkpointer
        if store is not None:
            agent.store = store

        # 5. Set interrupt nodes
        if interrupt_before:
            agent.interrupt_before_nodes = interrupt_before
        if interrupt_after:
            agent.interrupt_after_nodes = interrupt_after

        # 6. Build LangGraph stream_mode list
        #    "events" is NOT a valid astream mode — skip it
        #    "messages-tuple" maps to LangGraph's "messages" mode
        lg_modes: list[str] = []
        for m in requested_modes:
            if m == "messages-tuple":
                lg_modes.append("messages")
            elif m == "events":
                # Skipped — see log above
                continue
            elif m in _VALID_LG_MODES:
                lg_modes.append(m)
        if not lg_modes:
            lg_modes = ["values"]

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for m in lg_modes:
            if m not in seen:
                seen.add(m)
                deduped.append(m)
        lg_modes = deduped

        logger.info("Run %s: streaming with modes %s (requested: %s)", run_id, lg_modes, requested_modes)

        # 7. Stream using graph.astream
        if len(lg_modes) == 1 and not stream_subgraphs:
            # Single mode, no subgraphs: astream yields raw chunks
            single_mode = lg_modes[0]
            async for chunk in agent.astream(graph_input, config=runnable_config, stream_mode=single_mode):
                if record.abort_event.is_set():
                    logger.info("Run %s abort requested — stopping", run_id)
                    break
                sse_event = _lg_mode_to_sse_event(single_mode)
                await bridge.publish(run_id, sse_event, serialize(chunk, mode=single_mode))
        else:
            # Multiple modes or subgraphs: astream yields tuples
            async for item in agent.astream(
                graph_input,
                config=runnable_config,
                stream_mode=lg_modes,
                subgraphs=stream_subgraphs,
            ):
                if record.abort_event.is_set():
                    logger.info("Run %s abort requested — stopping", run_id)
                    break

                mode, chunk = _unpack_stream_item(item, lg_modes, stream_subgraphs)
                if mode is None:
                    continue

                sse_event = _lg_mode_to_sse_event(mode)
                await bridge.publish(run_id, sse_event, serialize(chunk, mode=mode))

        # 8. Final status
        if record.abort_event.is_set():
            action = record.abort_action
            if action == "rollback":
                await run_manager.set_status(run_id, RunStatus.error, error="Rolled back by user")
                try:
                    await _rollback_checkpoint(
                        checkpointer, thread_id=thread_id, pre_checkpoint_id=pre_run_checkpoint_id
                    )
                    logger.info("Run %s rolled back", run_id)
                except Exception:
                    logger.warning("Failed to rollback checkpoint for run %s", run_id)
            else:
                await run_manager.set_status(run_id, RunStatus.interrupted)
        else:
            await run_manager.set_status(run_id, RunStatus.success)

    except asyncio.CancelledError:
        action = record.abort_action
        if action == "rollback":
            await run_manager.set_status(run_id, RunStatus.error, error="Rolled back by user")
            logger.info("Run %s was cancelled (rollback)", run_id)
        else:
            await run_manager.set_status(run_id, RunStatus.interrupted)
            logger.info("Run %s was cancelled", run_id)

    except Exception as exc:
        error_msg = f"{exc}"
        logger.exception("Run %s failed: %s", run_id, error_msg)
        await run_manager.set_status(run_id, RunStatus.error, error=error_msg)
        await bridge.publish(
            run_id,
            "error",
            {
                "message": error_msg,
                "name": type(exc).__name__,
            },
        )

    finally:
        await bridge.publish_end(run_id)
        asyncio.create_task(bridge.cleanup(run_id, delay=60))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lg_mode_to_sse_event(mode: str) -> str:
    """Map LangGraph internal stream_mode name to SSE event name.

    LangGraph's ``astream(stream_mode="messages")`` produces message
    tuples.  The SSE protocol calls this ``messages-tuple`` when the
    client explicitly requests it, but the default SSE event name used
    by LangGraph Platform is simply ``"messages"``.
    """
    # All LG modes map 1:1 to SSE event names — "messages" stays "messages"
    return mode


def _unpack_stream_item(
    item: Any,
    lg_modes: list[str],
    stream_subgraphs: bool,
) -> tuple[str | None, Any]:
    """Unpack a multi-mode or subgraph stream item into (mode, chunk).

    Returns ``(None, None)`` if the item cannot be parsed.
    """
    if stream_subgraphs:
        if isinstance(item, tuple) and len(item) == 3:
            _ns, mode, chunk = item
            return str(mode), chunk
        if isinstance(item, tuple) and len(item) == 2:
            mode, chunk = item
            return str(mode), chunk
        return None, None

    if isinstance(item, tuple) and len(item) == 2:
        mode, chunk = item
        return str(mode), chunk

    # Fallback: single-element output from first mode
    return lg_modes[0] if lg_modes else None, item
