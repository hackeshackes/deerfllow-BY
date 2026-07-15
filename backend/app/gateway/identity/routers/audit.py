"""Audit query and export API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.gateway.auth import require_owner_user
from ..audit.query import export_events_csv
from ..audit.writer import get_audit_writer

router = APIRouter(
    prefix="/api/admin/audit",
    tags=["audit"],
    dependencies=[Depends(require_owner_user)],
)


@router.get("/events")
async def query_events(
    actor_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
) -> dict:
    writer = get_audit_writer()
    events = await writer.query(
        actor_id=actor_id, workspace_id=workspace_id, action=action, limit=limit,
    )
    return {
        "events": [
            {
                "id": e.id, "occurred_at": e.occurred_at, "actor_id": e.actor_id,
                "actor_type": e.actor_type.value, "action": e.action,
                "resource_type": e.resource_type, "resource_id": e.resource_id,
                "workspace_id": e.workspace_id, "metadata": e.metadata,
                "success": e.success,
            }
            for e in events
        ]
    }


@router.get("/export", response_class=PlainTextResponse)
async def export_events(
    format: str = Query(default="csv", pattern="^csv$"),
    workspace_id: Optional[str] = None,
) -> PlainTextResponse:
    writer = get_audit_writer()
    events = await writer.query(workspace_id=workspace_id, limit=10000)
    body = export_events_csv(events)
    return PlainTextResponse(content=body, media_type="text/csv")