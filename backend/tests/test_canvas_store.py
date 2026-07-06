"""Tests for the v1.6.x canvas `WorkflowStore` Protocol + `InMemoryWorkflowStore`.

These exercise the default process-local implementation that backs the
canvas CRUD surface. Task A7 will add a SQLite-backed store; until
then, the in-memory implementation is the canonical reference for
the `WorkflowStore` Protocol contract.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.gateway.canvas.models import NodeKind, Workflow, WorkflowNode, WorkflowStatus
from app.gateway.canvas.store import InMemoryWorkflowStore


def _node(id_: str = "n1") -> WorkflowNode:
    return WorkflowNode(id=id_, kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0))


def _workflow(id_: str = "w1", workspace_id: str = "ws1", version: int = 1) -> Workflow:
    return Workflow(
        id=id_,
        name="demo",
        workspace_id=workspace_id,
        status=WorkflowStatus.DRAFT,
        nodes=(_node(),),
        edges=(),
        version=version,
        created_at=datetime(2026, 7, 6, tzinfo=UTC),
        updated_at=datetime(2026, 7, 6, tzinfo=UTC),
    )


def test_upsert_first_time_sets_version_to_1():
    store = InMemoryWorkflowStore()
    saved = store.upsert(_workflow(version=0))
    assert saved.version == 1


def test_upsert_existing_increments_version():
    store = InMemoryWorkflowStore()
    first = store.upsert(_workflow())
    second = store.upsert(first)
    assert second.version == first.version + 1


def test_list_by_workspace_filters_other_workspaces():
    store = InMemoryWorkflowStore()
    store.upsert(_workflow("w1", workspace_id="ws-a"))
    store.upsert(_workflow("w2", workspace_id="ws-b"))
    only_a = store.list_by_workspace("ws-a")
    assert {w.id for w in only_a} == {"w1"}


def test_delete_removes_workflow():
    store = InMemoryWorkflowStore()
    store.upsert(_workflow())
    store.delete("w1")
    assert store.get("w1") is None


def test_get_returns_none_for_unknown_id():
    store = InMemoryWorkflowStore()
    assert store.get("missing") is None
