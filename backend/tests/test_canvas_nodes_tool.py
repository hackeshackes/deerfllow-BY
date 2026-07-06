"""Unit tests for canvas ToolNode executor (v1.6.x Task A6).

ToolNode delegates invocation to a `ToolRegistry` Protocol defined
locally (no direct harness import).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.gateway.canvas.nodes.base import NodeOutput
from app.gateway.canvas.nodes.tool import ToolNode


class _FakeRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(self, name: str, **kwargs: Any) -> Any:
        self.calls.append({"name": name, **kwargs})
        return {"value": f"{name}:{kwargs.get('q', '')}"}


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
        def call(self, name: str, **kwargs: Any) -> Any:
            raise KeyError(name)

    node = ToolNode(registry=_Empty())  # type: ignore[arg-type]
    out = await node.execute(config={"tool_name": "missing", "args": {}}, inputs={})
    assert out.error is not None
