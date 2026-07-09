"""Smoke check that the v1.6.x lifespan wires the canvas router to a
real (sqlite-backed) store via MICX_CANVAS_STORE=sqlite.

Regression coverage for the v1.6.1 follow-up: previously the router
was included but never ``configure()``d, so POST /api/workflows would
503. After the fix, picking the sqlite backend at construction time
must round-trip a workflow that survives the lifespan exit.
"""

from __future__ import annotations

from pathlib import Path


def test_lifespan_wires_canvas_router_to_sqlite_store(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "lifespan.db"
    monkeypatch.setenv("MICX_CANVAS_STORE", "sqlite")
    monkeypatch.setenv("MICX_CANVAS_DB", str(db_path))

    from app.gateway.app import create_app

    app = create_app()
    # The store should be reachable on app.state so admin scripts can
    # poke at the database directly without going through the router.
    assert hasattr(app.state, "canvas_store")
    assert app.state.canvas_store.__class__.__name__ == "SqliteWorkflowStore"

    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.post(
        "/api/workflows",
        json={
            "name": "lifespan-wired",
            "workspace_id": "ws1",
            "nodes": [{"id": "n1", "kind": "prompt", "config": {}, "position": [0.0, 0.0]}],
            "edges": [],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    wf_id = body["id"]
    assert body["version"] == 1

    # GET to prove the row landed on disk (not just in the in-process dict).
    resp2 = client.get(f"/api/workflows/{wf_id}")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["name"] == "lifespan-wired"
