"""Tests for ``app.gateway.canvas.executor`` (Task A7).

The ``WorkflowExecutor`` composes every node kind that ships in v1.6.x
(A2: prompt, A3: branch, A4: loop, plus the TBD agent/tool slots). These
tests verify the linear / fail-fast / propagation semantics without
touching any live runtime — every node executor is faked.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from app.gateway.canvas.executor import WorkflowExecutor
from app.gateway.canvas.models import (
    NodeKind,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowStatus,
)
from app.gateway.canvas.nodes.base import NodeOutput


class _EchoPrompt:
    """Returns config['template'].upper() as outputs['text']."""

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        return NodeOutput(outputs={"text": config.get("template", "").upper()})


class _Match:
    def __init__(self, matched: bool) -> None:
        self._matched = matched

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        return NodeOutput(outputs={"matched": self._matched})


class _Loop:
    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        return NodeOutput(outputs={"iterations": int(config["iterations"])})


def _wf(nodes, edges, workspace_id="ws1") -> Workflow:
    return Workflow(
        id="w1",
        name="demo",
        workspace_id=workspace_id,
        status=WorkflowStatus.DRAFT,
        nodes=nodes,
        edges=edges,
        version=1,
        created_at=datetime(2026, 7, 6, tzinfo=UTC),
        updated_at=datetime(2026, 7, 6, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_linear_workflow_runs_nodes_in_order():
    wf = _wf(
        nodes=(
            WorkflowNode(id="a", kind=NodeKind.PROMPT, config={"template": "alpha"}, position=(0.0, 0.0)),
            WorkflowNode(id="b", kind=NodeKind.PROMPT, config={"template": "beta"}, position=(0.0, 0.0)),
        ),
        edges=(WorkflowEdge(id="e1", source_node_id="a", target_node_id="b"),),
    )
    ex = WorkflowExecutor(
        node_executors={
            NodeKind.PROMPT: _EchoPrompt(),
        },
    )
    result = await ex.execute(wf, inputs={})
    assert [s.node_id for s in result.steps] == ["a", "b"]
    assert result.outputs == {"a": {"text": "ALPHA"}, "b": {"text": "BETA"}}
    assert result.failed_node_id is None


@pytest.mark.asyncio
async def test_node_failure_default_fail_fast_false_continues():
    class _Boom:
        async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
            return NodeOutput(outputs={}, error="boom")

    wf = _wf(
        nodes=(
            WorkflowNode(id="a", kind=NodeKind.PROMPT, config={"template": "x"}, position=(0.0, 0.0)),
            WorkflowNode(id="b", kind=NodeKind.PROMPT, config={"template": "y"}, position=(0.0, 0.0)),
        ),
        edges=(WorkflowEdge(id="e1", source_node_id="a", target_node_id="b"),),
    )
    ex = WorkflowExecutor(node_executors={NodeKind.PROMPT: _Boom()})
    result = await ex.execute(wf, inputs={})
    assert all(s.error for s in result.steps)
    assert result.outputs == {}
    assert result.failed_node_id is None


@pytest.mark.asyncio
async def test_loop_node_records_iterations_in_step():
    wf = _wf(
        nodes=(WorkflowNode(id="loop1", kind=NodeKind.LOOP, config={"iterations": 3}, position=(0.0, 0.0)),),
        edges=(),
    )
    ex = WorkflowExecutor(node_executors={NodeKind.LOOP: _Loop()})
    result = await ex.execute(wf, inputs={})
    assert result.steps[0].outputs == {"iterations": 3}


@pytest.mark.asyncio
async def test_fail_fast_true_aborts_on_first_error():
    class _Boom:
        async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
            return NodeOutput(outputs={}, error="boom")

    wf = _wf(
        nodes=(
            WorkflowNode(id="a", kind=NodeKind.PROMPT, config={"template": "x"}, position=(0.0, 0.0)),
            WorkflowNode(id="b", kind=NodeKind.PROMPT, config={"template": "y"}, position=(0.0, 0.0)),
        ),
        edges=(WorkflowEdge(id="e1", source_node_id="a", target_node_id="b"),),
    )
    ex = WorkflowExecutor(node_executors={NodeKind.PROMPT: _Boom()}, fail_fast=True)
    result = await ex.execute(wf, inputs={})
    assert result.failed_node_id == "a"
    assert len(result.steps) == 1


@pytest.mark.asyncio
async def test_missing_executor_for_kind_marks_step_failed():
    """If no executor registered for a NodeKind, the step is marked failed (not crashed)."""
    wf = _wf(
        nodes=(WorkflowNode(id="a", kind=NodeKind.PROMPT, config={"template": "x"}, position=(0.0, 0.0)),),
        edges=(),
    )
    ex = WorkflowExecutor(node_executors={})  # empty registry
    result = await ex.execute(wf, inputs={})
    assert result.steps[0].status == "failed"
    assert "no executor" in (result.steps[0].error or "")
    assert result.failed_node_id is None  # default fail_fast=False


@pytest.mark.asyncio
async def test_branch_routes_to_true_edge_only_when_matched():
    """BRANCH node with `matched=True` runs the `condition='true'` edge target and skips the `condition='false'` one.

    Plan v1.6.x self-audit item: executor was previously running all nodes
    linearly regardless of branch condition. This locks the routing
    behavior so callers can rely on the executor picking a side.
    """
    wf = _wf(
        nodes=(
            WorkflowNode(id="br", kind=NodeKind.BRANCH, config={"condition": "x == 1"}, position=(0.0, 0.0)),
            WorkflowNode(id="t", kind=NodeKind.PROMPT, config={"template": "true-branch"}, position=(0.0, 0.0)),
            WorkflowNode(id="f", kind=NodeKind.PROMPT, config={"template": "false-branch"}, position=(0.0, 0.0)),
        ),
        edges=(
            WorkflowEdge(id="e1", source_node_id="br", target_node_id="t", condition="true"),
            WorkflowEdge(id="e2", source_node_id="br", target_node_id="f", condition="false"),
        ),
    )
    ex = WorkflowExecutor(
        node_executors={
            NodeKind.BRANCH: _Match(matched=True),
            NodeKind.PROMPT: _EchoPrompt(),
        },
    )
    result = await ex.execute(wf, inputs={})
    # Only the branch node + the true-branch target should run; the
    # `condition='false'` target is recorded as a skipped step so the
    # user can see in the trace that the unselected branch was
    # intentionally bypassed.
    assert [s.node_id for s in result.steps] == ["br", "t", "f"]
    statuses = {s.node_id: s.status for s in result.steps}
    assert statuses["br"] == "ok"
    assert statuses["t"] == "ok"
    assert statuses["f"] == "skipped"
    assert result.outputs.get("t") == {"text": "TRUE-BRANCH"}
    assert "f" not in result.outputs


@pytest.mark.asyncio
async def test_loop_repeats_downstream_subgraph_iterations_times():
    """A LOOP node followed by a single downstream node runs the downstream node `iterations` times.

    Each iteration appends a step record tagged with `metadata.iteration`.
    Output for the downstream node accumulates as a list under its id
    so callers can see per-iteration values.
    """
    wf = _wf(
        nodes=(
            WorkflowNode(id="loop1", kind=NodeKind.LOOP, config={"iterations": 3}, position=(0.0, 0.0)),
            WorkflowNode(id="body", kind=NodeKind.PROMPT, config={"template": "x"}, position=(0.0, 0.0)),
        ),
        edges=(WorkflowEdge(id="e1", source_node_id="loop1", target_node_id="body"),),
    )
    ex = WorkflowExecutor(
        node_executors={
            NodeKind.LOOP: _Loop(),
            NodeKind.PROMPT: _EchoPrompt(),
        },
    )
    result = await ex.execute(wf, inputs={})
    # 1 loop sentinel step + 3 body steps.
    body_steps = [s for s in result.steps if s.node_id == "body"]
    assert len(body_steps) == 3
    assert [s.metadata.get("iteration") for s in body_steps] == [1, 2, 3]
    # Accumulated outputs as a list, one entry per iteration.
    assert result.outputs["body"] == [
        {"text": "X"},
        {"text": "X"},
        {"text": "X"},
    ]
