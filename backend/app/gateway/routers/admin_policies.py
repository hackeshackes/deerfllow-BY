"""Owner-only admin ABAC policies API (v1.7 M2.6).

GET /api/admin/policies   → current policy set (from operator file or presets)
PUT /api/admin/policies   → validate + replace the operator policies file

Both are owner-only via ``require_abac``. Writes are validated by the M2.2
loader before persisting, so an invalid policy never lands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.gateway.abac.deps import require_abac
from app.gateway.abac.policies_file import validate_policy_dict
from app.gateway.auth import AuthUser

router = APIRouter(prefix="/api/admin/policies", tags=["admin-policies"])

# Operator policy file path; configured at startup (None → built-in presets).
_POLICY_FILE: str | None = None


def configure_policies_file(path: str | None) -> None:
    """Point the admin policies API at the operator file path."""
    global _POLICY_FILE
    _POLICY_FILE = path


class PoliciesResponse(BaseModel):
    version: int = 1
    policies: list[dict[str, Any]]


def _policy_to_dict(p: Any) -> dict[str, Any]:
    """Render an AttributePolicy into its declarative (editor-friendly) dict."""
    return {
        "id": p.name,
        "effect": p.effect,
        "combiner": p.combinator,
        "applies_to": [v[0] for v in p.applies_to],
        "conditions": [
            {"op": op.kind, "path": op.lhs, "value": op.rhs} for op in p.operators
        ],
    }


def _current_policy_dicts() -> list[dict[str, Any]]:
    """Serialize the active policy set (from file, else built-in presets)."""
    from app.gateway.abac.policies import OwnerOnlyPolicy, WorkspaceMemberPolicy

    if _POLICY_FILE and Path(_POLICY_FILE).exists():
        from app.gateway.abac.policies_file import load_policies_file

        return [_policy_to_dict(p) for p in load_policies_file(_POLICY_FILE)]

    return [
        _policy_to_dict(OwnerOnlyPolicy()),
        _policy_to_dict(WorkspaceMemberPolicy()),
    ]


@router.get("", response_model=PoliciesResponse)
def get_policies(_user: AuthUser = Depends(require_abac("read", "admin-policies"))):
    return PoliciesResponse(version=1, policies=_current_policy_dicts())


@router.put("", response_model=PoliciesResponse)
def put_policies(
    body: PoliciesResponse,
    _user: AuthUser = Depends(require_abac("write", "admin-policies")),
):
    if not _POLICY_FILE:
        raise HTTPException(status_code=503, detail="policies file not configured")
    if not body.policies:
        raise HTTPException(status_code=400, detail="at least one policy required")
    try:
        for pol in body.policies:
            validate_policy_dict(pol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path = Path(_POLICY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": body.version, "policies": body.policies}, indent=2),
        encoding="utf-8",
    )
    return PoliciesResponse(version=body.version, policies=body.policies)


__all__ = ["configure_policies_file", "router"]