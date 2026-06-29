"""Unified connectors API.

Exposes three surfaces:
- `GET    /api/connectors`           — list registered connectors
- `GET    /api/connectors/dlq`       — list DLQ entries (admin triage)
- `DELETE /api/connectors/dlq/{id}`  — drop a single DLQ entry
- `POST   /api/connectors/{name}/webhook` — inbound webhook from external IM

The DLQ store and webhook bridge are module-level singletons for now;
production will wire them through DI so that tests can isolate state.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..dlq import InMemoryDLQStore
from ..registry import get_registry
from ..webhook import WebhookBridge

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

# Module-level singletons (replace with DI in production)
_dlq = InMemoryDLQStore()
_bridge = WebhookBridge()


def get_dlq_store() -> InMemoryDLQStore:
    return _dlq


def get_webhook_bridge() -> WebhookBridge:
    return _bridge


@router.get("")
async def list_connectors() -> dict:
    reg = get_registry()
    return {
        "connectors": [
            {"name": c.name, "display_name": c.display_name}
            for c in (reg.get(n) for n in reg.list_names())
        ]
    }


@router.get("/dlq")
async def list_dlq(limit: int = Query(default=100, le=500, ge=1)) -> dict:
    return {"items": _dlq.list_all(limit=limit)}


@router.delete("/dlq/{item_id}", status_code=204)
async def delete_dlq(item_id: str) -> None:
    if not _dlq.delete(item_id):
        raise HTTPException(status_code=404, detail="dlq entry not found")


@router.post("/{name}/webhook")
async def handle_webhook(name: str, secret: str, payload: dict) -> dict:
    try:
        messages = await _bridge.handle_inbound(name, secret, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {
        "messages": [
            {"text": m.text, "target": m.target, "metadata": m.metadata}
            for m in messages
        ]
    }
