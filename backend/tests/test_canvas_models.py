"""Tests for the v1.6.x canvas domain models.

These exercise the frozen-dataclass invariants for `WorkflowNode`,
`WorkflowEdge`, and `Workflow`. They are deliberately written before
the implementation lives in `app.gateway.canvas.models`.
"""

from __future__ import annotations

import pytest

from app.gateway.canvas.models import (
    NodeKind,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowStatus,  # noqa: F401  (re-exported per spec)
)


def test_node_kind_must_be_known():
    with pytest.raises(ValueError, match="Unknown NodeKind"):
        WorkflowNode(id="n1", kind="not-a-kind", config={}, position=(0.0, 0.0))


def test_loop_node_iterations_bounds():
    with pytest.raises(ValueError, match="iterations"):
        WorkflowNode(id="n1", kind=NodeKind.LOOP, config={"iterations": 0}, position=(0.0, 0.0))
    with pytest.raises(ValueError, match="iterations"):
        WorkflowNode(id="n1", kind=NodeKind.LOOP, config={"iterations": 1001}, position=(0.0, 0.0))


def test_branch_node_requires_condition_string():
    with pytest.raises(ValueError, match="condition"):
        WorkflowNode(id="n1", kind=NodeKind.BRANCH, config={}, position=(0.0, 0.0))
    with pytest.raises(ValueError, match="condition"):
        WorkflowNode(id="n1", kind=NodeKind.BRANCH, config={"condition": ""}, position=(0.0, 0.0))


def test_workflow_requires_non_empty_name():
    n = WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0))
    with pytest.raises(ValueError, match="name"):
        Workflow(id="w1", name="", workspace_id="ws1", nodes=(n,), edges=())


def test_workflow_requires_workspace_id():
    n = WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0))
    with pytest.raises(ValueError, match="workspace_id"):
        Workflow(id="w1", name="demo", workspace_id="", nodes=(n,), edges=())


def test_workflow_edge_must_reference_existing_nodes():
    n1 = WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0))
    e = WorkflowEdge(id="e1", source_node_id="n1", target_node_id="missing")
    with pytest.raises(ValueError, match="unknown node"):
        Workflow(id="w1", name="demo", workspace_id="ws1", nodes=(n1,), edges=(e,))


def test_workflow_is_immutable():
    n = WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0))
    wf = Workflow(id="w1", name="demo", workspace_id="ws1", nodes=(n,), edges=())
    with pytest.raises(Exception):  # FrozenInstanceError
        wf.name = "new"  # type: ignore[misc]
