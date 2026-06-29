"""Tests for the subscriptions API."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.subscriptions.routers import subscriptions as sub_router
from app.gateway.subscriptions.routers.subscriptions import router


@pytest.fixture(autouse=True)
def _reset_store():
    sub_router._reset_store()
    yield
    sub_router._reset_store()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_subscribe_creates_entry(client):
    resp = client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "t-1", "notify_via": ["inapp"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["target_kind"] == "thread"
    assert body["target_id"] == "t-1"
    assert body["notify_via"] == ["inapp"]
    assert body["id"].startswith("sub-")


def test_subscribe_default_channels(client):
    resp = client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "t-2"},
    )
    assert resp.status_code == 201
    assert resp.json()["notify_via"] == ["inapp"]


def test_subscribe_rejects_unknown_kind(client):
    resp = client.post(
        "/api/subscriptions",
        json={"target_kind": "widget", "target_id": "x", "notify_via": ["inapp"]},
    )
    assert resp.status_code == 422


def test_subscribe_rejects_empty_id(client):
    resp = client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "", "notify_via": ["inapp"]},
    )
    assert resp.status_code == 422


def test_subscribe_rejects_unknown_channel(client):
    resp = client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "t-3", "notify_via": ["sms"]},
    )
    assert resp.status_code == 422


def test_count_returns_zero_for_unknown_target(client):
    resp = client.get("/api/subscriptions/thread/does-not-exist/count")
    assert resp.status_code == 200
    assert resp.json() == {"count": 0}


def test_count_returns_after_subscribe(client):
    client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "t-1", "notify_via": ["inapp"]},
    )
    resp = client.get("/api/subscriptions/thread/t-1/count")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_unsubscribe_removes(client):
    client.post(
        "/api/subscriptions",
        json={"target_kind": "thread", "target_id": "t-1", "notify_via": ["inapp"]},
    )
    resp = client.delete("/api/subscriptions/thread/t-1")
    assert resp.status_code == 204
    # Count should be zero after delete
    assert client.get("/api/subscriptions/thread/t-1/count").json()["count"] == 0
