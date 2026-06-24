import pytest
from app.gateway.connectors.base import BaseConnector, ConnectorMessage, ConnectorResponse

class FakeConnector(BaseConnector):
    name = "fake"
    display_name = "Fake Connector"

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        return ConnectorResponse(success=True, external_id="ext-1")

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        return []

def test_connector_abstract_methods():
    with pytest.raises(TypeError):
        BaseConnector()  # type: ignore

def test_fake_connector_send():
    import asyncio
    c = FakeConnector()
    msg = ConnectorMessage(text="hi", target={"chat_id": "x"})
    resp = asyncio.run(c.send(msg))
    assert resp.success is True
    assert resp.external_id == "ext-1"

def test_connector_message_defaults():
    m = ConnectorMessage(text="hi")
    assert m.target == {}
    assert m.attachments == []

def test_connector_response_error_field():
    r = ConnectorResponse(success=False, error="rate limited")
    assert r.error == "rate limited"
