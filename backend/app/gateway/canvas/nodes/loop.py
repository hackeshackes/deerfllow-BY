from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import NodeOutput


class LoopNode:
    """Loop sentinel. The executor reads `iterations` from config and
    repeats the body N times. This node itself returns the count so the
    step record shows the planned iterations."""

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        n = config.get("iterations", 1)
        if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 1000:
            return NodeOutput(outputs={}, error="LOOP iterations must be int in [1, 1000]")
        return NodeOutput(outputs={"iterations": n})
