import asyncio
import pytest
from app.gateway.identity.audit.writer import AuditWriter
from app.gateway.identity.audit.models import AuditEvent, ActorType


@pytest.fixture
def writer(tmp_path):
    return AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=2, flush_interval=0.1)


@pytest.mark.asyncio
async def test_write_single_event_persists(tmp_path):
    w = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=10, flush_interval=0.05)
    e = AuditEvent(actor_id="u-1", action="thread.create", resource_type="thread")
    await w.write(e)
    await w.flush()
    rows = await w.query(actor_id="u-1")
    assert len(rows) == 1
    assert rows[0].action == "thread.create"


@pytest.mark.asyncio
async def test_batch_flush_at_threshold(tmp_path):
    w = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=2, flush_interval=10.0)  # never auto-flushes
    for i in range(3):
        await w.write(AuditEvent(actor_id=f"u-{i}", action="x", resource_type="y"))
    await asyncio.sleep(0.01)  # let the writer task process
    # After 2 events, batch should have flushed; 3rd is pending
    assert len(await w.query()) >= 2


@pytest.mark.asyncio
async def test_query_filter_by_workspace(tmp_path):
    w = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=10, flush_interval=0.05)
    await w.write(AuditEvent(actor_id="u", action="a", resource_type="r", workspace_id="ws-1"))
    await w.write(AuditEvent(actor_id="u", action="a", resource_type="r", workspace_id="ws-2"))
    await w.flush()
    rows = await w.query(workspace_id="ws-1")
    assert all(r.workspace_id == "ws-1" for r in rows)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_writer_close_flushes_pending(tmp_path):
    w = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=100, flush_interval=10.0)
    await w.write(AuditEvent(actor_id="u", action="a", resource_type="r"))
    await w.close()
    rows = await w.query()
    assert len(rows) == 1