"""End-to-end: middleware captures event, query retrieves it."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.gateway.identity.audit.middleware import AuditMiddleware
from app.gateway.identity.audit.writer import AuditWriter
from app.gateway.identity.audit.models import ActorType


@pytest.mark.asyncio
async def test_full_flow(tmp_path):
    app = FastAPI()
    writer = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=10, flush_interval=0.05)
    app.add_middleware(
        AuditMiddleware,
        writer=writer,
        actor_resolver=lambda req: ("u-test", ActorType.USER),
    )

    @app.post("/api/test")
    async def endpoint():
        return {"ok": True}

    client = TestClient(app)
    client.post("/api/test")
    await writer.flush()

    events = await writer.query(actor_id="u-test")
    assert any(e.action == "api.create" for e in events)
    await writer.close()