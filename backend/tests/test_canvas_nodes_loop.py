"""Unit tests for canvas LoopNode executor (v1.6.x Task A6).

LoopNode is a sentinel that returns the planned iteration count so the
`WorkflowExecutor` (Task A7) can iterate the body `n` times.
"""

from __future__ import annotations

import pytest

from app.gateway.canvas.nodes.base import NodeOutput
from app.gateway.canvas.nodes.loop import LoopNode


@pytest.mark.asyncio
async def test_loop_returns_iterations():
    node = LoopNode()
    out = await node.execute(config={"iterations": 3}, inputs={})
    assert isinstance(out, NodeOutput)
    assert out.outputs == {"iterations": 3}
    assert out.error is None


@pytest.mark.asyncio
async def test_loop_validates_iterations_bounds():
    """LoopNode re-checks the iterations bound (defense in depth — WorkflowNode
    also validates, but LoopNode is callable directly in tests)."""
    node = LoopNode()
    out = await node.execute(config={"iterations": 0}, inputs={})
    assert out.error is not None
    assert "iterations" in out.error


@pytest.mark.asyncio
async def test_loop_validates_upper_bound():
    node = LoopNode()
    out = await node.execute(config={"iterations": 1001}, inputs={})
    assert out.error is not None
    assert "iterations" in out.error


@pytest.mark.asyncio
async def test_loop_rejects_bool_iterations():
    """Python bool is a subclass of int — LoopNode must explicitly reject True/False."""
    node = LoopNode()
    out = await node.execute(config={"iterations": True}, inputs={})  # type: ignore[dict-item]
    assert out.error is not None
