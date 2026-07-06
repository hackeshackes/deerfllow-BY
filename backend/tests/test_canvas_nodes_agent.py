"""Unit tests for canvas AgentNode executor (v1.6.x Task A6).

AgentNode delegates chat to a `DeerFlowClient`-shaped `AgentClient`
Protocol defined locally (no direct harness import).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.gateway.canvas.nodes.agent import AgentNode
from app.gateway.canvas.nodes.base import NodeOutput


class _FakeClient:
    def __init__(self, reply: str) -> None:
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
