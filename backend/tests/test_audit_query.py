import pytest
from app.gateway.identity.audit.writer import AuditWriter
from app.gateway.identity.audit.query import export_events_csv
from app.gateway.identity.audit.models import AuditEvent


@pytest.mark.asyncio
async def test_export_csv(tmp_path):
    w = AuditWriter(db_path=str(tmp_path / "audit.db"), batch_size=10, flush_interval=0.05)
    await w.write(AuditEvent(actor_id="u-1", action="thread.create", resource_type="thread", resource_id="t-1"))
    await w.write(AuditEvent(actor_id="u-2", action="skill.enable", resource_type="skill", resource_id="s-1"))
    await w.flush()
    events = await w.query()
    csv = export_events_csv(events)
    lines = csv.splitlines()
    assert lines[0].startswith("id,occurred_at,actor_id,actor_type,action")
    assert len(lines) == 3  # header + 2 rows
    assert "thread.create" in csv
    assert "skill.enable" in csv
    await w.close()