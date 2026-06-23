import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.gateway.identity.audit.middleware import AuditMiddleware
from app.gateway.identity.audit.writer import AuditWriter
from app.gateway.identity.audit.models import ActorType


@pytest.fixture
def app_and_writer(tmp_path):
    app = FastAPI()
    writer = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=10, flush_interval=0.05)
    app.add_middleware(AuditMiddleware, writer=writer, actor_resolver=lambda req: ("u-1", ActorType.USER))

    @app.post("/threads")
    async def create_thread(req: Request):
        return {"id": "t-1"}

    @app.delete("/threads/{tid}")
    async def delete_thread(tid: str, req: Request):
        return {"deleted": tid}

    return app, writer


@pytest.mark.asyncio
async def test_post_creates_audit_event(app_and_writer):
    app, writer = app_and_writer
    c = TestClient(app)
    c.post("/threads", json={"title": "x"})
    await writer.flush()
    events = await writer.query(actor_id="u-1")
    actions = [e.action for e in events]
    assert "threads.create" in actions


@pytest.mark.asyncio
async def test_delete_creates_audit_event(app_and_writer):
    app, writer = app_and_writer
    c = TestClient(app)
    c.delete("/threads/t-1")
    await writer.flush()
    events = await writer.query(action="threads.delete")
    assert len(events) >= 1