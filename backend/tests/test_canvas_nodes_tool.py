"""Unit tests for canvas ToolNode (v1.6.x Task A6).

Covers the NodeExecutor Protocol contract via the concrete ToolNode,
which delegates to a ToolRegistry Protocol so the harness runtime
can be injected at app construction without importing deerflow.* here.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.gateway.canvas.nodes.base import NodeOutput
from app.gateway.canvas.nodes.tool import ToolNode


class _FakeRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(self, name: str, **kwargs):
        self.calls.append({"name": name, **kwargs})
        return {"value": f"{name}:{kwargs.get('q', '')}"}


class _ScalarRegistry:
    """Returns a non-dict value to exercise the wrap-into-{"value": ...} branch."""

    def call(self, name: str, **kwargs):
        return 42


@pytest.mark.asyncio
async def test_tool_node_invokes_registry_with_args():
    reg = _FakeRegistry()
    node = ToolNode(registry=reg)  # type: ignore[arg-type]
    out = await node.execute(
        config={"tool_name": "search", "args": {"q": "deerflow"}},
        inputs={},
    )
    assert isinstance(out, NodeOutput)
    assert out.outputs == {"value": "search:deerflow"}
    assert reg.calls == [{"name": "search", "q": "deerflow"}]


@pytest.mark.asyncio
async def test_tool_node_unknown_tool_returns_error():
    class _Empty:
        def call(self, name: str, **kwargs):
            raise KeyError(name)

    node = ToolNode(registry=_Empty())  # type: ignore[arg-type]
    out = await node.execute(config={"tool_name": "missing", "args": {}}, inputs={})
    assert out.error is not None
    assert "unknown tool" in out.error


@pytest.mark.asyncio
async def test_tool_node_inputs_override_config_args():
    """Spec §3.3: workflow inputs WIN on conflict with config args.

    Regression test for the high-priority bug found by code-quality review on
    commit b773791e — the original `args.setdefault(k, v)` was inverted.
    """
    reg = _FakeRegistry()
    node = ToolNode(registry=reg)  # type: ignore[arg-type]
    out = await node.execute(
        config={"tool_name": "search", "args": {"q": "from-config"}},
        inputs={"q": "from-inputs"},
    )
    assert out.error is None
    assert reg.calls == [{"name": "search", "q": "from-inputs"}]


@pytest.mark.asyncio
async def test_tool_node_inputs_fill_missing_config_args():
    """Workflow inputs fill in keys that config did not provide."""
    reg = _FakeRegistry()
    node = ToolNode(registry=reg)  # type: ignore[arg-type]
    out = await node.execute(
        config={"tool_name": "search", "args": {"q": "from-config"}},
        inputs={"extra": "value"},
    )
    assert out.error is None
    assert reg.calls == [{"name": "search", "q": "from-config", "extra": "value"}]


@pytest.mark.asyncio
async def test_tool_node_non_dict_registry_return_wrapped_in_value():
    """ToolRegistry can return scalars; ToolNode wraps them in {value: ...}."""
    node = ToolNode(registry=_ScalarRegistry())  # type: ignore[arg-type]
    out = await node.execute(
        config={"tool_name": "count", "args": {}},
        inputs={},
    )
    assert out.error is None
    assert out.outputs == {"value": 42}
