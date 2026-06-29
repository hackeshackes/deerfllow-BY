"""Tests for the unified connectors FastAPI router."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.connectors.routers.connectors import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_connectors_empty(client):
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connectors"] == []


def test_get_dlq_empty(client):
    resp = client.get("/api/connectors/dlq")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_webhook_endpoint_returns_403_for_bad_secret(client):
    """Without a registered route + valid secret, the webhook should 403 or 404."""
    resp = client.post(
        "/api/connectors/feishu/webhook",
        params={"secret": "invalid"},
        json={"text": "hi"},
    )
    # Either 403 (invalid secret) or 404 (no connector) is acceptable.
    assert resp.status_code in (403, 404)


def test_dlq_delete_missing_returns_404(client):
    resp = client.delete("/api/connectors/dlq/does-not-exist")
    assert resp.status_code == 404


def test_dlq_list_respects_limit(client):
    resp = client.get("/api/connectors/dlq", params={"limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
