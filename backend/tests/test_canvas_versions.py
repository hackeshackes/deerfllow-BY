"""Tests for the v1.6.x canvas version manager (Task A3)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.gateway.canvas.models import NodeKind, Workflow, WorkflowNode, WorkflowStatus
from app.gateway.canvas.store import InMemoryWorkflowStore
from app.gateway.canvas.versions import (
    InMemoryVersionStore,
    VersionManager,
    WorkflowVersion,  # noqa: F401  (re-export smoke-checked via package import)
)


def _workflow(id_: str = "w1", workspace_id: str = "ws1", name: str = "demo") -> Workflow:
    return Workflow(
        id=id_,
        name=name,
        workspace_id=workspace_id,
        status=WorkflowStatus.DRAFT,
        nodes=(WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0)),),
        edges=(),
        version=1,
        created_at=datetime(2026, 7, 6, tzinfo=UTC),
        updated_at=datetime(2026, 7, 6, tzinfo=UTC),
    )


def test_commit_creates_version_record():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    mgr = VersionManager(wstore, vstore)
    wf = wstore.upsert(_workflow())
    v = mgr.commit(wf)
    assert v.workflow_id == "w1"
    assert v.version == wf.version
    assert v.snapshot == wf


def test_list_versions_returns_chronological_order():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    mgr = VersionManager(wstore, vstore)
    wf1 = wstore.upsert(_workflow())
    mgr.commit(wf1)
    wf2 = wstore.upsert(wf1)
    mgr.commit(wf2)
    versions = mgr.list_versions("w1")
    assert [v.version for v in versions] == [1, 2]


def test_rollback_restores_old_version_as_new_version():
    wstore = InMemoryWorkflowStore()
    vstore = InMemoryVersionStore()
    mgr = VersionManager(wstore, vstore)
    wf1 = wstore.upsert(_workflow())
    mgr.commit(wf1)
    wf2 = wstore.upsert(replace(wf1, name="v2"))
    mgr.commit(wf2)
    rolled = mgr.rollback("w1", version=1)
    assert rolled.name == "demo"
    assert rolled.version == wf2.version + 1
    assert wstore.get("w1") == rolled
