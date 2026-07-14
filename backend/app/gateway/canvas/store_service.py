"""Canvas store factory (v1.6.1).

Resolves the ``WorkflowStore`` + ``VersionStore`` pair at app
construction time based on the ``MICX_CANVAS_STORE`` env var:

* ``memory`` (default) — ``InMemoryWorkflowStore`` + ``InMemoryVersionStore``,
  cold-start friendly, dev default.
* ``sqlite`` — ``SqliteWorkflowStore`` + ``SqliteVersionStore`` backed
  by a file (default ``backend/.deer-flow/canvas.db``; override with
  ``MICX_CANVAS_DB``). Survives gateway restarts.

Reads env vars fresh on each invocation so test fixtures that set the
env mid-process pick up the right backend (same pattern as
``app.gateway.comments.service``).
"""

from __future__ import annotations

import os
from typing import Protocol

from .store import InMemoryWorkflowStore, WorkflowStore
from .versions import InMemoryVersionStore, VersionStore


class StorePair(Protocol):
    workflow: WorkflowStore
    version: VersionStore


def get_canvas_store_and_versions() -> tuple[WorkflowStore, VersionStore]:
    """Return ``(workflow_store, version_store)`` based on ``MICX_CANVAS_STORE``."""
    backend = os.environ.get("MICX_CANVAS_STORE", "memory").lower()
    if backend == "sqlite":
        # import lazily so the memory default does not require the sqlite import path
        from .persistence.sqlite_store import (
            SqliteVersionStore,
            SqliteWorkflowStore,
        )

        db_path = os.environ.get("MICX_CANVAS_DB", ".deer-flow/canvas.db")
        return SqliteWorkflowStore(db_path), SqliteVersionStore(db_path)
    return InMemoryWorkflowStore(), InMemoryVersionStore()


def get_canvas_execution_store():
    """Return a fresh ``SqliteExecutionStore`` when MICX_CANVAS_STORE=sqlite,
    otherwise ``None`` so callers can detect the memory-backed deployment.

    Split out of ``get_canvas_store_and_versions`` because the executions
    table is opt-in (memory consumers don't need the extra store) and the
    router endpoints must keep working on memory deployments.
    """
    backend = os.environ.get("MICX_CANVAS_STORE", "memory").lower()
    if backend != "sqlite":
        return None
    # Lazy import for the same reason as the parent factory.
    from .persistence.sqlite_store import SqliteExecutionStore

    db_path = os.environ.get("MICX_CANVAS_DB", ".deer-flow/canvas.db")
    return SqliteExecutionStore(db_path)
