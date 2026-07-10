"""Tests for cross-workspace thread publishing (v1.6.x B2).

Tests the async ``PublishService`` against an in-memory ``_FakeStore`` that
mirrors the langgraph Store API shape (``aget`` / ``aput`` returning /
accepting dicts, namespaced under ``("threads",)``).

Scenarios:
1. ``publish()`` creates a new thread in the target workspace with lineage
2. Chain publishing preserves the original source (A -> B -> C, C.original == A)
3. ``publish_history`` is capped at 50 entries
4. ``publish()`` on a missing source thread raises ``LookupError``
5. FastAPI router end-to-end with a fake Store (integration)
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.collaboration.publish import (
    PUBLISH_HISTORY_MAX,
    PublishService,
)

# ---------------------------------------------------------------------------
# Fake Store
# ---------------------------------------------------------------------------


class _Item:
    """Minimal langgraph Store Item shape (just ``.value``)."""

    def __init__(self, value: dict) -> None:
        self.value = value


class _FakeStore:
    """In-memory Store-like for unit/integration tests.

    Mirrors the langgraph Store surface used by ``PublishService``:
    ``async aget(ns, key) -> Item | None`` and ``async aput(ns, key, value)``.
    """

    def __init__(self) -> None:
        # Records indexed by (namespace, key). Tests inspect ``records``
        # directly to assert on persisted state.
        self.records: dict[tuple[tuple[str, ...], str], dict] = {}

    async def aget(self, ns: tuple[str, ...], key: str) -> Any | None:
        record = self.records.get((ns, key))
        if record is None:
            return None
        return _Item(record)

    async def aput(self, ns: tuple[str, ...], key: str, value: dict) -> None:
        self.records[(ns, key)] = value


def _seed_thread(store: _FakeStore, thread_id: str, **meta_overrides: Any) -> None:
    """Put a minimal thread record in the fake store."""
    metadata: dict = {}
    metadata.update(meta_overrides)
    store.records[(("threads",), thread_id)] = {
        "thread_id": thread_id,
        "status": "idle",
        "created_at": 0.0,
        "updated_at": 0.0,
        "metadata": metadata,
        "values": None,
    }


def _ns_record(store: _FakeStore, thread_id: str) -> dict:
    return store.records[(("threads",), thread_id)]


# ---------------------------------------------------------------------------
# Unit tests — PublishService against the fake Store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_creates_new_thread_in_target_workspace():
    fake = _FakeStore()
    _seed_thread(fake, "A")
    svc = PublishService(store=fake)

    result = await svc.publish(
        source_thread_id="A",
        target_workspace_id="ws-b",
        actor_user_id="u1",
    )

    assert result.new_thread_id != "A"
    assert result.source_thread_id == "A"
    assert result.target_workspace_id == "ws-b"
    assert result.original_thread_id == "A"

    new = _ns_record(fake, result.new_thread_id)
    assert new["status"] == "idle"
    assert new["metadata"]["published_from_thread_id"] == "A"
    assert new["metadata"]["publish_target_workspace_id"] == "ws-b"
    assert new["metadata"]["publish_actor_user_id"] == "u1"


@pytest.mark.asyncio
async def test_chain_publish_preserves_original_source():
    fake = _FakeStore()
    _seed_thread(fake, "A")
    svc = PublishService(store=fake)

    b_result = await svc.publish("A", "ws-b", "u1")
    c_result = await svc.publish(b_result.new_thread_id, "ws-c", "u1")

    assert c_result.original_thread_id == "A"
    c_record = _ns_record(fake, c_result.new_thread_id)
    assert c_record["metadata"]["published_from_thread_id"] == "A"


@pytest.mark.asyncio
async def test_history_is_capped_at_50():
    fake = _FakeStore()
    pre = {
        "publish_history": [
            {
                "new_thread_id": f"old-{i}",
                "target_workspace_id": "ws-old",
                "actor_user_id": "u1",
                "at": 0.0,
            }
            for i in range(PUBLISH_HISTORY_MAX - 1)
        ]
    }
    _seed_thread(fake, "A", **pre)
    svc = PublishService(store=fake)

    await svc.publish("A", "ws-b", "u1")

    history = _ns_record(fake, "A")["metadata"]["publish_history"]
    assert len(history) == PUBLISH_HISTORY_MAX


@pytest.mark.asyncio
async def test_publish_missing_source_thread_raises():
    fake = _FakeStore()
    svc = PublishService(store=fake)

    with pytest.raises(LookupError):
        await svc.publish("missing", "ws-b", "u1")


# ---------------------------------------------------------------------------
# Integration test — FastAPI router end-to-end with fake Store
# ---------------------------------------------------------------------------


def _override_user():
    return AuthUser(
        id="u1",
        email="u@x.com",
        role="owner",  # OwnerOnlyPolicy path — bypasses workspace membership
        name="U",
        status="active",
        password_hash="x",
        salt="y",
    )


def test_router_post_publish_and_history_via_fake_store():
    """POST/GET /api/threads/{id}/publish exercise the router + service + fake store."""
    from app.gateway.collaboration.routers.publish import (
        configure,
        reset_for_tests,
    )
    from app.gateway.collaboration.routers.publish import (
        router as publish_router,
    )

    fake = _FakeStore()
    _seed_thread(fake, "A")
    configure(PublishService(store=fake))

    try:
        app = FastAPI()
        app.include_router(publish_router)
        app.dependency_overrides[require_user] = _override_user

        with TestClient(app) as client:
            resp = client.post(
                "/api/threads/A/publish",
                json={"target_workspace_id": "ws-b"},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["original_thread_id"] == "A"
            assert body["source_thread_id"] == "A"
            assert body["target_workspace_id"] == "ws-b"
            assert body["new_thread_id"] != "A"

            history_resp = client.get("/api/threads/A/publish-history")
            assert history_resp.status_code == 200, history_resp.text
            events = history_resp.json()["events"]
            assert len(events) == 1
            assert events[0]["new_thread_id"] == body["new_thread_id"]
            assert events[0]["target_workspace_id"] == "ws-b"
            assert events[0]["actor_user_id"] == "u1"
    finally:
        reset_for_tests()


def test_router_404_when_source_thread_missing():
    """POST /api/threads/{id}/publish returns 404 if the source doesn't exist."""
    from app.gateway.collaboration.routers.publish import (
        configure,
        reset_for_tests,
    )
    from app.gateway.collaboration.routers.publish import (
        router as publish_router,
    )

    fake = _FakeStore()
    configure(PublishService(store=fake))

    try:
        app = FastAPI()
        app.include_router(publish_router)
        app.dependency_overrides[require_user] = _override_user

        with TestClient(app) as client:
            resp = client.post(
                "/api/threads/missing/publish",
                json={"target_workspace_id": "ws-b"},
            )
            assert resp.status_code == 404
            assert "missing" in resp.json()["detail"]
    finally:
        reset_for_tests()


def test_router_503_when_service_not_configured():
    """Calling without configure() returns 503 — proves wiring is required."""
    from app.gateway.collaboration.routers.publish import (
        reset_for_tests,
    )
    from app.gateway.collaboration.routers.publish import (
        router as publish_router,
    )

    reset_for_tests()
    app = FastAPI()
    app.include_router(publish_router)
    app.dependency_overrides[require_user] = _override_user

    with TestClient(app) as client:
        resp = client.post(
            "/api/threads/anything/publish",
            json={"target_workspace_id": "ws-b"},
        )
        assert resp.status_code == 503


def test_router_abac_denies_member_when_workspace_membership_empty():
    """v1.6.1: ABAC evaluates before the service runs. A 'member'
    user with no workspace membership is denied (no policy matches)."""
    from app.gateway.collaboration.routers.publish import (
        configure,
        reset_for_tests,
    )
    from app.gateway.collaboration.routers.publish import (
        router as publish_router,
    )

    fake = _FakeStore()
    _seed_thread(fake, "A")
    configure(PublishService(store=fake))

    def member_no_workspaces():
        return AuthUser(
            id="u2",
            email="u2@x.com",
            role="member",  # not owner → WorkspaceMemberPolicy must allow
            name="U2",
            status="active",
            password_hash="x",
            salt="y",
        )

    try:
        app = FastAPI()
        app.include_router(publish_router)
        app.dependency_overrides[require_user] = member_no_workspaces

        with TestClient(app) as client:
            resp = client.post(
                "/api/threads/A/publish",
                json={"target_workspace_id": "ws-b"},
            )
            # ABAC fail-closed → 403 before any thread lookup is done.
            assert resp.status_code == 403, resp.text
            assert "no matching policy" in resp.text
    finally:
        reset_for_tests()