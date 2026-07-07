from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Protocol

from .base import NodeOutput

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class AgentClient(Protocol):
    """Subset of deerflow.client.DeerFlowClient used by AgentNode.

    Defined here as a Protocol so tests can pass a fake without importing
    the full client (which requires the harness runtime).
    """

    def chat(self, message: str, thread_id: str) -> str: ...


class AgentNode:
    """Delegate a chat turn to an `AgentClient`.

    Implements the `NodeExecutor` Protocol: `execute(config, inputs)`.

    - Renders `{{var}}` placeholders in `config["prompt"]` against `inputs`
      (same pattern as `PromptNode`).
    - Calls `client.chat(rendered, thread_id=self._thread_id)`.
    - Returns `{"text": reply}` on success; surfaces client errors as
      `NodeOutput.error` so the `WorkflowExecutor` (Task A7) can record the
      step as failed.
    """

    def __init__(self, client: AgentClient, default_thread_id: str) -> None:
        self._client = client
        self._thread_id = default_thread_id

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        prompt = config.get("prompt", "")
        if not isinstance(prompt, str):
            return NodeOutput(outputs={}, error="agent.prompt must be a string")
        missing = sorted({m.group(1) for m in _VAR_RE.finditer(prompt)} - set(inputs.keys()))
        if missing:
            return NodeOutput(outputs={}, error=f"missing variables: {missing}")
        rendered = _VAR_RE.sub(lambda m: str(inputs[m.group(1)]), prompt)
        try:
            reply = self._client.chat(rendered, thread_id=self._thread_id)
        except Exception as exc:  # noqa: BLE001 — surface as NodeOutput.error
            return NodeOutput(outputs={}, error=f"agent error: {exc}")
        return NodeOutput(outputs={"text": reply})
