import pytest
from fastapi.testclient import TestClient
from app.gateway.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_query_audit_events(client):
    resp = client.get("/api/admin/audit/events?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)


def test_export_audit_csv(client):
    resp = client.get("/api/admin/audit/export?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert resp.text.startswith("id,occurred_at,actor_id,actor_type,action")