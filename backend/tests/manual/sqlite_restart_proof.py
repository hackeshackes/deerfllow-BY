"""End-to-end cross-process restart verification for v1.6.1 SQLite.

Runs two fresh Python interpreters against the same SQLite file:

* process A — writes a workflow then exits
* process B — reads it back

The subprocess boundary is what makes this a true restart test —
any module-level cache that survived the write process would be
caught by the second process starting cold.

Run manually with::

    cd backend && PYTHONPATH=. python tests/manual/sqlite_restart_proof.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def _phase_env(phase: str, db: str, workflow_id: str, name: str) -> dict[str, str]:
    env = {**os.environ, "PYTHONPATH": ".", "PHASE": phase}
    env["DB_PATH"] = db
    env["WF_ID"] = workflow_id
    env["WF_NAME"] = name
    return env


PHASE_BODY = r"""
import json
import os
from datetime import datetime, UTC
from app.gateway.canvas.persistence.sqlite_store import (
    SqliteVersionStore,
    SqliteWorkflowStore,
)
from app.gateway.canvas.models import (
    NodeKind,
    Workflow,
    WorkflowNode,
    WorkflowStatus,
)
from app.gateway.canvas.versions import VersionManager

db = os.environ["DB_PATH"]
wf_id = os.environ["WF_ID"]
wf_name = os.environ["WF_NAME"]
phase = os.environ["PHASE"]

wstore = SqliteWorkflowStore(db)
vstore = SqliteVersionStore(db)

if phase == "write":
    wf = Workflow(
        id=wf_id,
        name=wf_name,
        workspace_id="ws-restart",
        status=WorkflowStatus.DRAFT,
        nodes=(WorkflowNode(id="n1", kind=NodeKind.PROMPT, config={}, position=(0.0, 0.0)),),
        edges=(),
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    saved = wstore.upsert(wf)
    VersionManager(wstore, vstore).commit(saved)
    out = {"phase": "write", "id": saved.id, "version": saved.version}
    wstore.close(); vstore.close()
elif phase == "read":
    found = wstore.get(wf_id)
    out = {
        "phase": "read",
        "found": None if found is None else {
            "id": found.id,
            "name": found.name,
            "version": found.version,
            "workspace_id": found.workspace_id,
        },
    }
    wstore.close(); vstore.close()
else:
    raise SystemExit(f"unknown PHASE={phase!r}")

print("__RESULT__" + json.dumps(out))
"""


def _run(phase: str, db: str, wf_id: str, wf_name: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", PHASE_BODY],
        capture_output=True,
        text=True,
        env=_phase_env(phase, db, wf_id, wf_name),
        check=True,
        cwd=".",
    )
    lines = [line.removeprefix("__RESULT__") for line in proc.stdout.splitlines() if line.startswith("__RESULT__")]
    assert lines, f"{phase!r} subprocess produced no result; stderr={proc.stderr}"
    return json.loads(lines[-1])


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "restart.db")

        write_result = _run("write", db_path, "wf-restart-test", "cross-restart-survives")
        assert write_result["id"] == "wf-restart-test", write_result
        assert write_result["version"] == 1, write_result
        print("[phase A: write] ok:", write_result)

        read_result = _run("read", db_path, "wf-restart-test", "cross-restart-survives")
        print("[phase B: read] ok:", read_result)
        assert read_result["found"] is not None, "cross-restart failed: workflow vanished"
        assert read_result["found"]["id"] == "wf-restart-test"
        assert read_result["found"]["name"] == "cross-restart-survives"
        assert read_result["found"]["version"] == 1
        assert read_result["found"]["workspace_id"] == "ws-restart"

    print("CROSS-RESTART PROOF PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
