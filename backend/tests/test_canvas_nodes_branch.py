"""Unit tests for canvas BranchNode executor (v1.6.x Task A5).

`BranchNode` evaluates `var op value` conditions against a fixed set of
9 operators using a fixed AST evaluator — **never** Python `eval`/`exec`.
Missing variables, unsupported ops, and bad literals all surface as
`NodeOutput.error`.
"""

from __future__ import annotations

import pytest

from app.gateway.canvas.nodes.branch import BranchNode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cond,inputs,expected",
    [
        ("score == 100", {"score": 100}, True),
        ("score != 0", {"score": 5}, True),
        ("name == admin", {"name": "admin"}, True),
        ("status in {active,pending}", {"status": "active"}, True),
        ("n > 10", {"n": 11}, True),
        ("n < 10", {"n": 5}, True),
        ("n >= 10", {"n": 10}, True),
        ("n <= 10", {"n": 10}, True),
        ("tags contains alpha", {"tags": ["alpha", "beta"]}, True),
        ("email matches .*@example\\.com", {"email": "a@example.com"}, True),
    ],
)
async def test_branch_evaluates_supported_ops(cond, inputs, expected):
    node = BranchNode()
    out = await node.execute(config={"condition": cond}, inputs=inputs)
    assert out.error is None, out.error
    assert out.outputs == {"matched": expected}


@pytest.mark.asyncio
async def test_branch_unknown_op_returns_error():
    node = BranchNode()
    out = await node.execute(config={"condition": "score @ 100"}, inputs={"score": 100})
    assert out.error is not None


@pytest.mark.asyncio
async def test_branch_does_not_eval_or_exec():
    """Security: never use Python eval/exec — only fixed AST evaluator."""
    node = BranchNode()
    out = await node.execute(
        config={"condition": "__import__('os').system('echo pwn')"},
        inputs={},
    )
    assert out.error is not None
