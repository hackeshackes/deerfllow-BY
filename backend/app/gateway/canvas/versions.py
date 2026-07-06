"""Workflow versioning (v1.6.x, Task A3).

* `WorkflowVersion` — frozen record holding a complete `Workflow` snapshot
  plus the version number and a creation timestamp.
* `VersionStore` — Protocol defining the persistence contract for
  versions, mirroring how `WorkflowStore` separates the interface from
  the storage backend.
* `InMemoryVersionStore` — default process-local implementation. State
  is held in a private dict keyed by `workflow_id`; each bucket is kept
  sorted by `version` so `list()` always returns chronological order.
* `VersionManager` — coordinates `WorkflowStore` and `VersionStore`:

  - `commit(workflow)` snapshots the current workflow.
  - `list_versions(workflow_id)` returns the chronological history.
  - `rollback(workflow_id, version)` restores an old snapshot as a
    **new** version on top of the workflow store, then commits it.

`VersionManager` is deliberately a thin coordinator; it owns no state
of its own. Following the same composition pattern as
`QuotaService(InMemoryUsageTracker)`, it depends on the two Protocols
and accepts whatever concrete implementations the application wires in.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from .models import Workflow
from .store import WorkflowStore


@dataclass(frozen=True)
class WorkflowVersion:
    workflow_id: str
    version: int
    snapshot: Workflow
    created_at: datetime


class VersionStore(Protocol):
    def save(self, version: WorkflowVersion) -> None: ...
    def list(self, workflow_id: str) -> list[WorkflowVersion]: ...
    def get(self, workflow_id: str, version: int) -> WorkflowVersion | None: ...


class InMemoryVersionStore:
    """Default VersionStore implementation (v1.6.x).

    Process-local. For cross-restart durability, swap in a SQLite-backed
    implementation alongside the matching `WorkflowStore` replacement.
    """

    def __init__(self) -> None:
        self._by_workflow: dict[str, list[WorkflowVersion]] = {}

    def save(self, version: WorkflowVersion) -> None:
        bucket = self._by_workflow.setdefault(version.workflow_id, [])
        bucket.append(version)
        bucket.sort(key=lambda v: v.version)

    def list(self, workflow_id: str) -> list[WorkflowVersion]:
        return list(self._by_workflow.get(workflow_id, []))

    def get(self, workflow_id: str, version: int) -> WorkflowVersion | None:
        for v in self._by_workflow.get(workflow_id, []):
            if v.version == version:
                return v
        return None


class VersionManager:
    def __init__(self, store: WorkflowStore, versions: VersionStore) -> None:
        self._store = store
        self._versions = versions

    def commit(self, workflow: Workflow) -> WorkflowVersion:
        record = WorkflowVersion(
            workflow_id=workflow.id,
            version=workflow.version,
            snapshot=workflow,
            created_at=datetime.now(UTC),
        )
        self._versions.save(record)
        return record

    def list_versions(self, workflow_id: str) -> list[WorkflowVersion]:
        return self._versions.list(workflow_id)

    def rollback(self, workflow_id: str, version: int) -> Workflow:
        old = self._versions.get(workflow_id, version)
        if old is None:
            raise LookupError(f"version {version} not found for workflow {workflow_id}")
        current = self._store.get(workflow_id)
        if current is None:
            raise LookupError(f"workflow {workflow_id} not found")
        # Preserve the live WorkflowStatus — rolling back a PUBLISHED workflow to
        # a buggy draft should NOT silently re-publish it. Caller can override
        # via the A8 router's status field after rollback if they want a status swap.
        restored = self._store.upsert(replace(old.snapshot, status=current.status))
        self.commit(restored)
        return restored
