"""ABAC gate reads the operator policies file when wired (v1.7 M2 A).

Regression for the "two-path drift": once ``configure_abac_policies_path``
points ``require_abac`` at the same file the admin editor writes, an owner-gated
route must honour a file that denies an action it previously allowed via the
built-in presets. A missing file keeps the built-in presets (RBAC-equivalent).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.gateway.abac.deps import configure_abac_policies_path, require_abac
from app.gateway.auth import AuthUser, require_user


def _make_user(role: str) -> AuthUser:
    return AuthUser(
        id="u1",
        email="u@x.com",
        role=role,
        name="U",
        status="active",
        password_hash="x",
        salt="y",
    )


def _owner_gated_app() -> FastAPI:
    app = FastAPI()

    @app.get("/gate")
    def gate(_user: AuthUser = Depends(require_abac("read", "connector"))):
        return {"ok": True}

    return app


@pytest.fixture(autouse=True)
def _reset():
    configure_abac_policies_path(None)
    yield
    configure_abac_policies_path(None)


def test_missing_file_keeps_builtin_presets_owner_allowed():
    configure_abac_policies_path("/nonexistent/policies.json")
    app = _owner_gated_app()
    app.dependency_overrides[require_user] = lambda: _make_user("owner")
    with TestClient(app) as client:
        assert client.get("/gate").status_code == 200


def test_operator_file_overrides_builtin_presets(tmp_path: Path):
    """A file denying the connector/read verb beats the built-in owner-allow."""
    path = tmp_path / "policies.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [
                    {
                        "id": "deny-connector-read",
                        "effect": "deny",
                        "combiner": "all_of",
                        "applies_to": ["read"],
                        "conditions": [],
                    }
                ],
            }
        )
    )
    configure_abac_policies_path(str(path))
    app = _owner_gated_app()
    app.dependency_overrides[require_user] = lambda: _make_user("owner")
    with TestClient(app) as client:
        resp = client.get("/gate")
        assert resp.status_code == 403