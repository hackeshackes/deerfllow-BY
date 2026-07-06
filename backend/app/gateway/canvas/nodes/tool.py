from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .base import NodeOutput


class ToolRegistry(Protocol):
    """Subset of a tool-registry facade used by ToolNode.

    Defined here as a Protocol so tests can pass a fake without importing
    any concrete registry (MCP, builtin, community, etc.).
    """

    def call(self, name: str, **kwargs: Any) -> Any: ...


class ToolNode:
    """Invoke a registered tool by name.

    Implements the `NodeExecutor` Protocol: `execute(config, inputs)`.

    - `config["tool_name"]` is required (string).
    - `config["args"]` is an optional dict of tool arguments.
    - `inputs` may override or supply additional kwargs via `setdefault`,
      so node-config defaults can be supplemented — but not clobbered —
      by upstream workflow inputs.
    - Returns the registry result directly when it is a dict, otherwise
      wraps it as `{"value": result}`.
    - Unknown tools (`registry.call` raises `KeyError`) surface as
      `NodeOutput.error` so the `WorkflowExecutor` (Task A7) records the
      step as failed.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        name = config.get("tool_name", "")
        if not isinstance(name, str) or not name:
            return NodeOutput(outputs={}, error="tool_name is required")
        args = dict(config.get("args") or {})
        # Merge inputs last so node-config defaults can be supplemented by
        # workflow inputs without overwriting explicit args.
        for k, v in inputs.items():
            args.setdefault(k, v)
        try:
            result = self._registry.call(name, **args)
        except KeyError:
            return NodeOutput(outputs={}, error=f"unknown tool: {name}")
        except Exception as exc:  # noqa: BLE001 — surface as NodeOutput.error
            return NodeOutput(outputs={}, error=f"tool error: {exc}")
        return NodeOutput(outputs=result if isinstance(result, dict) else {"value": result})
