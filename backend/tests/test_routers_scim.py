import pytest
from fastapi.testclient import TestClient
from app.gateway.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_get_sync_state(client):
    resp = client.get("/api/admin/scim/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


def test_trigger_sync(client):
    resp = client.post("/api/admin/scim/sync/keycloak")
    # Without a real provider configured, expect 200 (no-op) or 404
    assert resp.status_code in (200, 404)