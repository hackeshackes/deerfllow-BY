from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class NodeOutput:
    outputs: Mapping[str, Any]
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class NodeExecutor(Protocol):
    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput: ...
