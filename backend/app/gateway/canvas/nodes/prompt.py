from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .base import NodeOutput

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class PromptNode:
    """Renders `{{var}}` placeholders against `inputs`.

    Implements the `NodeExecutor` Protocol: `execute(config, inputs)`.
    Missing variables produce NodeOutput.error; the workflow executor
    surfaces that as a failed step (Task A7).
    """

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        template = config.get("template", "")
        if not isinstance(template, str):
            return NodeOutput(outputs={}, error="template must be a string")
        missing = sorted({m.group(1) for m in _VAR_RE.finditer(template)} - set(inputs.keys()))
        if missing:
            return NodeOutput(outputs={}, error=f"missing variables: {missing}")
        rendered = _VAR_RE.sub(lambda m: str(inputs[m.group(1)]), template)
        return NodeOutput(outputs={"text": rendered})
