"""Unit tests for canvas AgentNode (v1.6.x Task A6).

Covers the NodeExecutor Protocol contract via the concrete AgentNode,
which delegates to an AgentClient Protocol so the harness runtime
can be injected at app construction without importing deerflow.* here.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.gateway.canvas.nodes.agent import AgentNode
from app.gateway.canvas.nodes.base import NodeOutput


class _FakeClient:
    def __init__(self, reply: str = "") -> None:
        self._reply = reply
        self.calls: list[dict[str, Any]] = []

    def chat(self, message: str, thread_id: str) -> str:
        self.calls.append({"message": message, "thread_id": thread_id})
        return self._reply


@pytest.mark.asyncio
async def test_agent_node_invokes_client_and_returns_text():
    client = _FakeClient(reply="hello back")
    node = AgentNode(client=client, default_thread_id="t-1")  # type: ignore[arg-type]
    out = await node.execute(
        config={"prompt": "say hi"},
        inputs={},
    )
    assert isinstance(out, NodeOutput)
    assert out.outputs == {"text": "hello back"}
    assert client.calls == [{"message": "say hi", "thread_id": "t-1"}]


@pytest.mark.asyncio
async def test_agent_node_renders_prompt_with_inputs():
    client = _FakeClient(reply="ok")
    node = AgentNode(client=client, default_thread_id="t-1")  # type: ignore[arg-type]
    out = await node.execute(
        config={"prompt": "echo {{word}}"},
        inputs={"word": "alpha"},
    )
    assert out.outputs == {"text": "ok"}
    assert client.calls[0]["message"] == "echo alpha"


@pytest.mark.asyncio
async def test_agent_node_missing_variable_returns_error():
    node = AgentNode(client=_FakeClient(), default_thread_id="t-1")  # type: ignore[arg-type]
    out = await node.execute(
        config={"prompt": "hello {{name}}"},
        inputs={},  # name missing
    )
    assert out.error is not None
    assert "name" in out.error
    assert "missing" in out.error.lower()


@pytest.mark.asyncio
async def test_agent_node_non_string_prompt_returns_error():
    node = AgentNode(client=_FakeClient(), default_thread_id="t-1")  # type: ignore[arg-type]
    out = await node.execute(
        config={"prompt": 123},  # type: ignore[dict-item]
        inputs={},
    )
    assert out.error is not None
