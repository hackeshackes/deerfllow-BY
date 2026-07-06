"""Unit tests for canvas node executors (v1.6.x Task A4).

Covers the `NodeExecutor` Protocol contract via the concrete `PromptNode`
implementation, which renders Jinja-like `{{var}}` placeholders against
workflow `inputs`.
"""

from __future__ import annotations

import pytest

from app.gateway.canvas.nodes.base import NodeOutput
from app.gateway.canvas.nodes.prompt import PromptNode


@pytest.mark.asyncio
async def test_prompt_renders_jinja_like_vars():
    node = PromptNode(config={"template": "hello {{name}}"})
    out = await node.execute(inputs={"name": "world"})
    assert isinstance(out, NodeOutput)
    assert out.outputs == {"text": "hello world"}
    assert out.error is None


@pytest.mark.asyncio
async def test_prompt_missing_var_returns_error():
    node = PromptNode(config={"template": "hello {{name}}"})
    out = await node.execute(inputs={})
    assert out.error is not None
    assert "name" in out.error


@pytest.mark.asyncio
async def test_prompt_static_template_no_vars():
    node = PromptNode(config={"template": "hello"})
    out = await node.execute(inputs={})
    assert out.outputs == {"text": "hello"}
