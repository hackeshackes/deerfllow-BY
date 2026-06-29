"""Spaces API (personal / workspace)."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/spaces", tags=["spaces"])


class Space(BaseModel):
    id: str
    name: str
    type: str  # "personal" | "workspace"


# Default space list. In production this is derived from the user's
# actual workspace memberships via the identity subsystem.
_DEFAULT_SPACES: list[Space] = [
    Space(id="personal", name="Personal", type="personal"),
    Space(id="ws-product", name="Product Team", type="workspace"),
    Space(id="ws-engineering", name="Engineering", type="workspace"),
]


def _reset_default_spaces() -> None:
    """Reset the default space list — used by tests to isolate state."""
    global _DEFAULT_SPACES
    _DEFAULT_SPACES = [
        Space(id="personal", name="Personal", type="personal"),
        Space(id="ws-product", name="Product Team", type="workspace"),
        Space(id="ws-engineering", name="Engineering", type="workspace"),
    ]


@router.get("", response_model=dict)
async def list_spaces() -> dict:
    return {"spaces": [s.model_dump() for s in _DEFAULT_SPACES]}


@router.get("/current", response_model=Space)
async def current_space(
    x_micx_space: str | None = Header(default=None, alias="X-MicX-Space"),
) -> Space:
    """Read the current space from the `X-MicX-Space` header.

    Defaults to `personal` when the header is missing. Falls back to the
    first space if the requested id is unknown — the client may be lagging
    behind a deletion, and we don't want to break the UI.
    """
    sid = x_micx_space or "personal"
    for s in _DEFAULT_SPACES:
        if s.id == sid:
            return s
    # Unknown id: fall back to the first space (typically `personal`).
    return _DEFAULT_SPACES[0]


@router.get("/{space_id}", response_model=Space)
async def get_space(space_id: str) -> Space:
    for s in _DEFAULT_SPACES:
        if s.id == space_id:
            return s
    raise HTTPException(status_code=404, detail=f"space {space_id!r} not found")
