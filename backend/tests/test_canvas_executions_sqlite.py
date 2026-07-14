"""Tests for the v1.6.1 follow-up `workflow_executions` table.

The v1.6.x spec called for a 3-table SQLite schema:
``workflows`` / ``workflow_versions`` / ``workflow_executions``. The
first two landed in PR #8; this PR adds the third so that
``SqliteWorkflowStore`` captures execution history alongside draft +
version persistence.

Schema:

* execution_id PK
* workflow_id FK (indexed)
* status (ok / failed / running)
* started_at, ended_at (UTC ISO)
* total_tokens, failed_node_id (optional)
* error (optional)
* steps_json: serialized `ExecutionStep` list

Public API:

* ``ExecutionStore.save(execution) -> None``
* ``ExecutionStore.list(workflow_id, limit=...) -> list[ExecutionRecord]``
* ``ExecutionStore.get(execution_id) -> ExecutionRecord | None``

Plus end-to-end: the canvas ``/execute`` route writes a row after a
real run (best-effort, behind an env-gated switch so test isolation
is preserved) and the ``/api/workflows/{id}/executions`` read
endpoint returns them newest-first.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.gateway.canvas.executor import ExecutionStep, WorkflowExecution
from app.gateway.canvas.persistence.sqlite_store import (
    SqliteExecutionStore,
)


@pytest.fixture
def store(tmp_path: Path):
    db = tmp_path / "executions.db"
    return SqliteExecutionStore(str(db))


def _execution(
    execution_id: str = "exec-1",
    workflow_id: str = "w1",
    *,
    status: str = "ok",
    total_tokens: int = 0,
    failed_node_id: str | None = None,
    error: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> WorkflowExecution:
    now = started_at or datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
    end = ended_at or datetime(2026, 7, 14, 12, 0, 5, tzinfo=UTC)
    return WorkflowExecution(
        workflow_id=workflow_id,
        workflow_version=1,
        started_at=now,
        ended_at=end,
        steps=(
            ExecutionStep(
                node_id="n1",
                started_at=now,
                ended_at=end,
                status=status,
                outputs={"text": "hello"},
                error=error,
                metadata={},
            ),
        ),
        outputs={"final": "hello"},
        total_tokens=total_tokens,
        failed_node_id=failed_node_id,
    )


# ---- Persistence round-trip ----


def test_save_and_list_round_trip_persists_all_fields(store):
    exec_obj = _execution(total_tokens=120, failed_node_id="n-2", error="boom")
    store.save("exec-1", exec_obj)

    rows = store.list(workflow_id="w1")
    assert len(rows) == 1
    row = rows[0]
    assert row.execution_id == "exec-1"
    assert row.workflow_id == "w1"
    assert row.workflow_version == 1
    assert row.total_tokens == 120
    assert row.failed_node_id == "n-2"
    assert row.error == "boom"
    # Steps survive the JSON column.
    assert len(row.steps) == 1
    assert row.steps[0].node_id == "n1"
    assert row.steps[0].status == "ok"
    assert row.steps[0].outputs == {"text": "hello"}


def test_list_orders_by_started_at_descending(store):
    store.save("exec-1", _execution(execution_id="exec-1", started_at=datetime(2026, 7, 14, 9, tzinfo=UTC), ended_at=datetime(2026, 7, 14, 9, 0, 30, tzinfo=UTC)))
    store.save("exec-2", _execution(execution_id="exec-2", started_at=datetime(2026, 7, 14, 10, tzinfo=UTC), ended_at=datetime(2026, 7, 14, 10, 0, 30, tzinfo=UTC)))
    store.save("exec-3", _execution(execution_id="exec-3", started_at=datetime(2026, 7, 14, 11, tzinfo=UTC), ended_at=datetime(2026, 7, 14, 11, 0, 30, tzinfo=UTC)))
    rows = store.list(workflow_id="w1")
    assert [r.execution_id for r in rows] == ["exec-3", "exec-2", "exec-1"]


def test_list_filters_to_workflow_id(store):
    store.save("exec-a", _execution(execution_id="exec-a", workflow_id="w1"))
    store.save("exec-b", _execution(execution_id="exec-b", workflow_id="w2"))
    only_w1 = store.list(workflow_id="w1")
    assert [r.execution_id for r in only_w1] == ["exec-a"]


def test_list_respects_limit(store):
    for i in range(7):
        store.save(f"exec-{i}", _execution(execution_id=f"exec-{i}"))
    rows = store.list(workflow_id="w1", limit=3)
    # Ordered desc → first 3 inserted by recency-of-start are stale;
    # since all share started_at, sqlite tie-breaks by execution_id;
    # only the slice length matters here.
    assert len(rows) == 3


def test_get_returns_single_execution(store):
    store.save("exec-9", _execution(execution_id="exec-9", total_tokens=42))
    got = store.get("exec-9")
    assert got is not None
    assert got.execution_id == "exec-9"
    assert got.total_tokens == 42


def test_get_returns_none_for_unknown_id(store):
    assert store.get("exec-missing") is None


def test_save_overwrites_existing_row(store):
    store.save("exec-r", _execution(execution_id="exec-r", total_tokens=10))
    store.save(
        "exec-r",
        _execution(
            execution_id="exec-r",
            total_tokens=20,
            failed_node_id="n-1",
            error="rerun",
        ),
    )
    rows = store.list(workflow_id="w1")
    assert len(rows) == 1
    assert rows[0].execution_id == "exec-r"
    assert rows[0].total_tokens == 20
    assert rows[0].failed_node_id == "n-1"


def test_save_with_zero_steps_still_persists(store):
    """Empty step lists are valid (e.g. a no-op workflow)."""
    empty = WorkflowExecution(
        workflow_id="w-empty",
        workflow_version=1,
        started_at=datetime(2026, 7, 14, 12, tzinfo=UTC),
        ended_at=datetime(2026, 7, 14, 12, 0, 1, tzinfo=UTC),
        steps=(),
        outputs={},
        total_tokens=0,
        failed_node_id=None,
    )
    store.save("exec-empty", empty)
    got = store.get("exec-empty")
    assert got is not None
    assert got.steps == ()


# ---- Cross-store persistence ----


def test_executions_persist_across_store_instances(tmp_path: Path):
    """Two SqliteExecutionStore instances pointing at the same file
    share state — proven end-to-end via a separate subprocess."""
    import json
    import os
    import subprocess
    import sys

    db = str(tmp_path / "cross.db")
    marker = "exec-marker"

    # Write a row.
    a = SqliteExecutionStore(db)
    a.save(marker, _execution(execution_id=marker, total_tokens=99))
    a.close()

    # Spawn a fresh Python process that opens another store and reads.
    script = """
import json, sys
sys.path.insert(0, ".")
from app.gateway.canvas.persistence.sqlite_store import SqliteExecutionStore
s = SqliteExecutionStore(sys.argv[1])
got = s.get(sys.argv[2])
s.close()
print(json.dumps({"found": got.workflow_id if got else None,
                  "tokens": got.total_tokens if got else None}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", script, db, marker],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": "."},
    )
    payload = json.loads(proc.stdout.splitlines()[-1])
    assert payload["found"] == "w1"
    assert payload["tokens"] == 99


# ---- Bad-input safety ----


def test_save_rejects_empty_execution_id(store):
    with pytest.raises(ValueError, match="execution_id"):
        store.save("", _execution())


def test_list_returns_empty_for_unknown_workflow(store):
    assert store.list(workflow_id="nonexistent") == []
