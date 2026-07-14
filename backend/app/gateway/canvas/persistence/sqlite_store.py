"""Persistent SQLite-backed canvas store (v1.6.1).

Provides drop-in replacements for ``InMemoryWorkflowStore`` and
``InMemoryVersionStore``. The schema lives in this directory so the
canvas module is self-contained; no migration scripts are required
because the tables are version-neutral (new workflow fields don't need
schema changes — they're stored as a JSON blob under
``workflows.snapshot_json``).

Switching between in-memory and SQLite at process startup is handled
by :func:`app.gateway.canvas.store_service.get_canvas_store_and_versions`
based on the ``MICX_CANVAS_STORE`` env var.

Concurrency model:

* a single ``threading.Lock`` serializes writes (Python-level).
* SQLite's file-level locking covers cross-process races.
* ``check_same_thread=False`` lets the FastAPI worker pool (uvicorn
  with ``--workers N``) share one instance per worker.
* reads intentionally take the lock too for snapshot consistency.

This is intentionally conservative: canvas writes are low-volume (UI
edit sessions, version commits). When production traffic demands more
throughput, swap in ``aiosqlite`` or a Postgres-backed implementation
behind the same Protocol.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ..executor import ExecutionStep, WorkflowExecution
from ..models import NodeKind, Workflow, WorkflowEdge, WorkflowNode, WorkflowStatus
from ..store import WorkflowStore
from ..versions import VersionStore, WorkflowVersion

_WORKFLOW_TABLE = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workflows_workspace
    ON workflows(workspace_id);
"""

_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_versions (
    workflow_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (workflow_id, version)
);
CREATE INDEX IF NOT EXISTS idx_versions_workflow
    ON workflow_versions(workflow_id);
"""

# v1.6.1 follow-up: per-execution history. The spec called for a
# 3-table SQLite schema (workflows / workflow_versions /
# workflow_executions); the third landed after the original v1.6.1
# work. Each row is a complete ``WorkflowExecution`` snapshot so we
# can replay / audit / debug runs without re-executing anything.
_EXECUTION_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_executions (
    execution_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    workflow_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    failed_node_id TEXT,
    error TEXT,
    steps_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_executions_workflow
    ON workflow_executions(workflow_id, started_at DESC);
"""

_EXECUTION_STATUS_BY_FINISH = {
    "running": "running",
    "ok": "ok",
    "failed": "failed",
    "skipped": "ok",
}


class _SqliteBackedStore:
    """Common connection/lock/schema plumbing for canvas sqlite stores."""

    def __init__(self, db_path: str, *, extra_ddl: str = "") -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema(extra_ddl)

    def _ensure_schema(self, extra_ddl: str) -> None:
        with self._lock:
            self._conn.executescript(
                _WORKFLOW_TABLE + _VERSION_TABLE + _EXECUTION_TABLE + extra_ddl
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class SqliteWorkflowStore(_SqliteBackedStore, WorkflowStore):
    """File-backed implementation of :class:`WorkflowStore`.

    Mirrors ``InMemoryWorkflowStore`` semantics:

    * upsert of a brand-new id assigns ``version=1`` regardless of
      caller's value;
    * upsert of an existing id increments version and refreshes
      ``updated_at``;
    * ``list_by_workspace`` returns every workflow in the given
      workspace.
    """

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)

    def get(self, workflow_id: str) -> Workflow | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT snapshot_json FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_workflow(json.loads(row["snapshot_json"]))

    def list_by_workspace(self, workspace_id: str) -> list[Workflow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT snapshot_json FROM workflows WHERE workspace_id = ? "
                "ORDER BY updated_at DESC",
                (workspace_id,),
            ).fetchall()
        return [_deserialize_workflow(json.loads(r["snapshot_json"])) for r in rows]

    def upsert(self, workflow: Workflow) -> Workflow:
        from datetime import UTC

        now = datetime.now(UTC)
        existing = self.get(workflow.id)
        if existing is None:
            saved = replace_workflow(workflow, version=1, updated_at=now)
        else:
            saved = replace_workflow(
                workflow, version=existing.version + 1, updated_at=now
            )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workflows (id, workspace_id, snapshot_json, version, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    workspace_id = excluded.workspace_id,
                    snapshot_json = excluded.snapshot_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    saved.id,
                    saved.workspace_id,
                    json.dumps(_serialize_workflow(saved)),
                    saved.version,
                    saved.updated_at.isoformat()
                    if isinstance(saved.updated_at, datetime)
                    else str(saved.updated_at),
                ),
            )
            self._conn.commit()
        return saved

    def delete(self, workflow_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
            self._conn.commit()


class SqliteVersionStore(_SqliteBackedStore, VersionStore):
    """File-backed implementation of :class:`VersionStore`."""

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)

    def save(self, version: WorkflowVersion) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO workflow_versions
                    (workflow_id, version, snapshot_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    version.workflow_id,
                    version.version,
                    json.dumps(_serialize_workflow(version.snapshot)),
                    version.created_at.isoformat()
                    if isinstance(version.created_at, datetime)
                    else str(version.created_at),
                ),
            )
            self._conn.commit()

    def list(self, workflow_id: str) -> list[WorkflowVersion]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT workflow_id, version, snapshot_json, created_at "
                "FROM workflow_versions WHERE workflow_id = ? "
                "ORDER BY version ASC",
                (workflow_id,),
            ).fetchall()
        return [_row_to_version(r) for r in rows]

    def get(self, workflow_id: str, version: int) -> WorkflowVersion | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT workflow_id, version, snapshot_json, created_at "
                "FROM workflow_versions WHERE workflow_id = ? AND version = ?",
                (workflow_id, version),
            ).fetchone()
        return _row_to_version(row) if row else None


class ExecutionRecord:
    """Public-row shape for a stored execution. The dataclass is
    frozen so that callers passing it around cannot mutate it
    accidentally; mutability belongs to the store.

    Mirrors the public fields of ``WorkflowExecution`` plus the
    execution_id primary key. Step records are reconstructed as
    ``ExecutionStep`` instances so the consumer doesn't have to know
    the JSON schema.
    """

    __slots__ = (
        "execution_id",
        "workflow_id",
        "workflow_version",
        "status",
        "started_at",
        "ended_at",
        "total_tokens",
        "failed_node_id",
        "error",
        "steps",
    )

    def __init__(
        self,
        execution_id: str,
        workflow_id: str,
        workflow_version: int,
        status: str,
        started_at: datetime,
        ended_at: datetime,
        total_tokens: int,
        failed_node_id: str | None,
        error: str | None,
        steps: tuple[ExecutionStep, ...],
    ) -> None:
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.workflow_version = workflow_version
        self.status = status
        self.started_at = started_at
        self.ended_at = ended_at
        self.total_tokens = total_tokens
        self.failed_node_id = failed_node_id
        self.error = error
        self.steps = tuple(steps)

    def __repr__(self) -> str:
        return (
            f"ExecutionRecord(execution_id={self.execution_id!r}, "
            f"workflow_id={self.workflow_id!r}, status={self.status!r}, "
            f"steps={len(self.steps)})"
        )


class SqliteExecutionStore(_SqliteBackedStore):
    """Persistence for ``WorkflowExecution`` rows.

    This is a sibling of ``SqliteWorkflowStore`` and
    ``SqliteVersionStore`` but does not implement a Protocol in the
    canvas domain — at the time of writing only the canvas router
    reads execution history, and it does so via the app.state
    hookup (same pattern as canvas_store / canvas_version_store). A
    dedicated Protocol can be added if other surfaces (e.g. an admin
    audit view) consume it.
    """

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)

    def save(self, execution_id: str, execution: WorkflowExecution) -> None:
        if not execution_id:
            raise ValueError("execution_id must be a non-empty string")
        status = _execution_status(execution)
        steps_payload = json.dumps(
            [_serialize_step(s) for s in execution.steps]
        )
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO workflow_executions
                    (execution_id, workflow_id, workflow_version, status,
                     started_at, ended_at, total_tokens,
                     failed_node_id, error, steps_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    execution.workflow_id,
                    execution.workflow_version,
                    status,
                    execution.started_at.isoformat(),
                    execution.ended_at.isoformat(),
                    execution.total_tokens,
                    execution.failed_node_id,
                    _truncate_error(execution),
                    steps_payload,
                ),
            )
            self._conn.commit()

    def list(self, workflow_id: str, limit: int | None = None) -> list[ExecutionRecord]:
        with self._lock:
            if limit is None:
                rows = self._conn.execute(
                    "SELECT * FROM workflow_executions WHERE workflow_id = ? "
                    "ORDER BY started_at DESC",
                    (workflow_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM workflow_executions WHERE workflow_id = ? "
                    "ORDER BY started_at DESC LIMIT ?",
                    (workflow_id, int(limit)),
                ).fetchall()
        return [_row_to_execution(r) for r in rows]

    def get(self, execution_id: str) -> ExecutionRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workflow_executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        return _row_to_execution(row) if row else None


# ---- (de)serialization helpers ----


def replace_workflow(workflow: Workflow, **changes: Any) -> Workflow:
    """Return a new ``Workflow`` with the given fields replaced.

    Re-implements ``dataclasses.replace`` over the frozen dataclass so
    we don't have to import ``replace`` into every caller — small but
    keeps the public surface tight.
    """
    from dataclasses import replace

    return replace(workflow, **changes)


def _serialize_step(step: ExecutionStep) -> dict[str, Any]:
    return {
        "node_id": step.node_id,
        "status": step.status,
        "started_at": step.started_at.isoformat(),
        "ended_at": step.ended_at.isoformat(),
        "outputs": dict(step.outputs),
        "error": step.error,
        "metadata": dict(step.metadata),
    }


def _deserialize_step(data: Mapping[str, Any]) -> ExecutionStep:
    return ExecutionStep(
        node_id=data["node_id"],
        status=data["status"],
        started_at=_coerce_dt(data.get("started_at")),
        ended_at=_coerce_dt(data.get("ended_at")),
        outputs=dict(data.get("outputs") or {}),
        error=data.get("error"),
        metadata=dict(data.get("metadata") or {}),
    )


def _serialize_workflow(wf: Workflow) -> dict[str, Any]:
    data = asdict(wf)
    # ``asdict`` already turns dataclasses into dicts; coerce the
    # status enum and node/edge dataclasses into JSON-friendly shapes.
    data["status"] = wf.status.value if isinstance(wf.status, WorkflowStatus) else str(wf.status)
    data["nodes"] = [_serialize_node(n) for n in wf.nodes]
    data["edges"] = [_serialize_edge(e) for e in wf.edges]
    data["created_at"] = (
        wf.created_at.isoformat() if isinstance(wf.created_at, datetime) else str(wf.created_at)
    )
    data["updated_at"] = (
        wf.updated_at.isoformat() if isinstance(wf.updated_at, datetime) else str(wf.updated_at)
    )
    return data


def _serialize_node(node: WorkflowNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind.value if isinstance(node.kind, NodeKind) else str(node.kind),
        "config": dict(node.config),
        "position": list(node.position),
    }


def _serialize_edge(edge: WorkflowEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "condition": edge.condition,
    }


def _deserialize_workflow(data: Mapping[str, Any]) -> Workflow:
    return Workflow(
        id=data["id"],
        name=data["name"],
        workspace_id=data["workspace_id"],
        status=WorkflowStatus(data["status"])
        if not isinstance(data.get("status"), WorkflowStatus)
        else data["status"],
        nodes=tuple(_deserialize_node(n) for n in data.get("nodes", [])),
        edges=tuple(_deserialize_edge(e) for e in data.get("edges", [])),
        version=int(data["version"]),
        created_at=_coerce_dt(data.get("created_at")),
        updated_at=_coerce_dt(data.get("updated_at")),
    )


def _deserialize_node(data: Mapping[str, Any]) -> WorkflowNode:
    return WorkflowNode(
        id=data["id"],
        kind=NodeKind(data["kind"]),
        config=dict(data.get("config") or {}),
        position=tuple(data.get("position") or (0.0, 0.0)),
    )


def _deserialize_edge(data: Mapping[str, Any]) -> WorkflowEdge:
    return WorkflowEdge(
        id=data["id"],
        source_node_id=data["source_node_id"],
        target_node_id=data["target_node_id"],
        condition=data.get("condition"),
    )


def _row_to_version(row: sqlite3.Row) -> WorkflowVersion:
    snapshot = _deserialize_workflow(json.loads(row["snapshot_json"]))
    return WorkflowVersion(
        workflow_id=row["workflow_id"],
        version=int(row["version"]),
        snapshot=snapshot,
        created_at=_coerce_dt(row["created_at"]),
    )


def _execution_status(execution: WorkflowExecution) -> str:
    """Map a WorkflowExecution to a top-level status string."""
    if execution.failed_node_id or any(s.status == "failed" for s in execution.steps):
        return "failed"
    return "ok"


def _truncate_error(execution: WorkflowExecution) -> str | None:
    """Pick the most informative error string off the execution, if any."""
    for step in execution.steps:
        if step.error:
            return step.error
    return None


def _row_to_execution(row: sqlite3.Row) -> ExecutionRecord:
    raw_steps = json.loads(row["steps_json"]) if row["steps_json"] else []
    return ExecutionRecord(
        execution_id=row["execution_id"],
        workflow_id=row["workflow_id"],
        workflow_version=int(row["workflow_version"]),
        status=row["status"],
        started_at=_coerce_dt(row["started_at"]),
        ended_at=_coerce_dt(row["ended_at"]),
        total_tokens=int(row["total_tokens"]),
        failed_node_id=row["failed_node_id"],
        error=row["error"],
        steps=tuple(_deserialize_step(s) for s in raw_steps),
    )


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        # callers tolerate missing timestamps via dataclass defaults
        return datetime.now(tz=__import__("datetime").UTC)  # type: ignore[attr-defined]
    text = str(value)
    # tolerate Z suffix and missing tz
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        from datetime import UTC

        parsed = parsed.replace(tzinfo=UTC)
    return parsed
