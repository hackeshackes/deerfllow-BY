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


@pytest.mark.asyncio
async def test_branch_empty_condition_returns_error():
    node = BranchNode()
    out = await node.execute(config={"condition": ""}, inputs={})
    assert out.error is not None
    assert "non-empty" in out.error


@pytest.mark.asyncio
async def test_branch_non_string_condition_returns_error():
    node = BranchNode()
    out = await node.execute(config={"condition": 123}, inputs={})  # type: ignore[dict-item]
    assert out.error is not None


@pytest.mark.asyncio
async def test_branch_unparseable_condition_returns_error():
    node = BranchNode()
    out = await node.execute(
        config={"condition": "this is not a condition"},
        inputs={"this": 1, "is": 2, "not": 3, "a": 4, "condition": 5},
    )
    assert out.error is not None


@pytest.mark.asyncio
async def test_branch_missing_variable_returns_error():
    node = BranchNode()
    out = await node.execute(
        config={"condition": "score == 100"},
        inputs={},
    )
    assert out.error is not None
    assert "score" in out.error


@pytest.mark.asyncio
async def test_branch_type_mismatch_on_ordering_returns_error():
    node = BranchNode()
    out = await node.execute(
        config={"condition": "name > 5"},
        inputs={"name": "alice"},
    )
    # str vs int comparison fails in Python 3 — should surface as error, not crash
    assert out.error is not None


@pytest.mark.asyncio
async def test_branch_malformed_set_literal_returns_error():
    node = BranchNode()
    out = await node.execute(
        config={"condition": "status in {active,pending"},
        inputs={"status": "active"},
    )
    assert out.error is not None
    assert "set literal" in out.error or "malformed" in out.error


@pytest.mark.asyncio
async def test_branch_in_with_non_iterable_rhs_returns_error():
    node = BranchNode()
    out = await node.execute(
        config={"condition": "x in 42"},
        inputs={"x": 1},
    )
    assert out.error is not None


@pytest.mark.asyncio
async def test_branch_eq_returning_false_succeeds_not_errors():
    """== returning False is a valid boolean result, not an error."""
    node = BranchNode()
    out = await node.execute(
        config={"condition": "score == 0"},
        inputs={"score": 100},
    )
    assert out.error is None
    assert out.outputs == {"matched": False}
