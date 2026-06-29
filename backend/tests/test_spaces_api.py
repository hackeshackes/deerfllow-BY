"""Tests for the spaces API."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.spaces import api as spaces_api
from app.gateway.spaces.api import router


@pytest.fixture(autouse=True)
def _reset_spaces():
    spaces_api._reset_default_spaces()
    yield
    spaces_api._reset_default_spaces()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_spaces(client):
    resp = client.get("/api/spaces")
    assert resp.status_code == 200
    data = resp.json()
    ids = [s["id"] for s in data["spaces"]]
    assert "personal" in ids
    assert any(s["type"] == "workspace" for s in data["spaces"])


def test_get_current_space_default(client):
    resp = client.get("/api/spaces/current")
    assert resp.status_code == 200
    assert resp.json()["id"] == "personal"


def test_get_current_space_from_header(client):
    resp = client.get("/api/spaces/current", headers={"X-MicX-Space": "ws-product"})
    assert resp.status_code == 200
    assert resp.json()["id"] == "ws-product"
    assert resp.json()["name"] == "Product Team"


def test_get_current_space_unknown_falls_back_to_personal(client):
    resp = client.get("/api/spaces/current", headers={"X-MicX-Space": "ghost"})
    assert resp.status_code == 200
    assert resp.json()["id"] == "personal"


def test_get_space_by_id(client):
    resp = client.get("/api/spaces/ws-engineering")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Engineering"


def test_get_space_not_found(client):
    resp = client.get("/api/spaces/no-such-space")
    assert resp.status_code == 404
