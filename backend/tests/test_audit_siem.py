import pytest
import respx
from httpx import Response
from app.gateway.identity.audit.siem import SplunkExporter


@pytest.mark.asyncio
async def test_splunk_exporter_sends_event():
    exporter = SplunkExporter(
        hec_url="https://splunk.example.com:8088/services/collector/event",
        hec_token="token-123",
    )
    sent = []
    with respx.mock() as router:
        route = router.post("https://splunk.example.com:8088/services/collector/event").mock(
            side_effect=lambda req: (sent.append(req.content) or Response(200, json={"text": "Success", "code": 0}))
        )
        ok = await exporter.export_one({
            "id": "evt-1", "actor_id": "u-1", "action": "x", "resource_type": "r",
        })
        assert ok is True
        assert len(sent) == 1
        assert b"evt-1" in sent[0]