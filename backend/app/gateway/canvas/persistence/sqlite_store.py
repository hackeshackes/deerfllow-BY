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
            self._conn.executescript(_WORKFLOW_TABLE + _VERSION_TABLE + extra_ddl)
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


# ---- (de)serialization helpers ----


def replace_workflow(workflow: Workflow, **changes: Any) -> Workflow:
    """Return a new ``Workflow`` with the given fields replaced.

    Re-implements ``dataclasses.replace`` over the frozen dataclass so
    we don't have to import ``replace`` into every caller — small but
    keeps the public surface tight.
    """
    from dataclasses import replace

    return replace(workflow, **changes)


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
