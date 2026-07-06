"""WorkflowStore Protocol + InMemoryWorkflowStore.

`WorkflowStore` defines the persistence contract for the v1.6.x canvas
domain. Callers (the gateway CRUD routes, the version manager, the
executor) depend on the Protocol, not on a concrete implementation.

`InMemoryWorkflowStore` is the default process-local implementation.
State is held in a private dict and is lost on process restart. For
cross-restart durability, swap in `persistence.sqlite_store.SqliteWorkflowStore`
(Task A7, P1) at app construction time.

Versioning rule:

* `upsert` of a brand-new `Workflow` (id not present) records it at
  `version=1` regardless of the caller's value.
* `upsert` of an existing `Workflow` increments `version` by 1 and
  preserves all other fields the caller passed in.
* Each save also refreshes `updated_at` to the current UTC time,
  matching spec §3.2 line 216.

This is deliberately simple — no conditional updates, no optimistic
locking. Higher-level concerns (auth, soft delete, audit log) belong
in the gateway service layer, not the store.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from .models import Workflow


class WorkflowStore(Protocol):
    def get(self, workflow_id: str) -> Workflow | None: ...
    def list_by_workspace(self, workspace_id: str) -> list[Workflow]: ...
    def upsert(self, workflow: Workflow) -> Workflow: ...
    def delete(self, workflow_id: str) -> None: ...


class InMemoryWorkflowStore:
    """Default WorkflowStore implementation (v1.6.x).

    All state is process-local. For cross-restart durability use
    `persistence.sqlite_store.SqliteWorkflowStore` (Task A7, P1).
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Workflow] = {}

    def get(self, workflow_id: str) -> Workflow | None:
        return self._by_id.get(workflow_id)

    def list_by_workspace(self, workspace_id: str) -> list[Workflow]:
        return [w for w in self._by_id.values() if w.workspace_id == workspace_id]

    def upsert(self, workflow: Workflow) -> Workflow:
        existing = self._by_id.get(workflow.id)
        now = datetime.now(UTC)
        if existing is None:
            saved = replace(workflow, version=1, updated_at=now)
        else:
            saved = replace(workflow, version=existing.version + 1, updated_at=now)
        self._by_id[saved.id] = saved
        return saved

    def delete(self, workflow_id: str) -> None:
        self._by_id.pop(workflow_id, None)
