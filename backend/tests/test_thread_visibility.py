from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.gateway.auth import AuthUser
from app.gateway.ownership import (
    THREAD_OWNER_KEY,
    THREAD_VISIBILITY_KEY,
    THREAD_VISIBILITY_PRIVATE,
    THREAD_VISIBILITY_WORKSPACE,
    THREAD_WORKSPACE_KEY,
    can_manage_thread,
    can_read_thread,
)
from app.gateway.routers import threads as threads_router

OWNER = AuthUser(id="owner", email="owner@example.com", role="owner", name="Owner", status="active", password_hash="", salt="")
MEMBER = AuthUser(id="member", email="member@example.com", role="member", name="Member", status="active", password_hash="", salt="")
OUTSIDER = AuthUser(id="outsider", email="outsider@example.com", role="member", name="Outsider", status="active", password_hash="", salt="")


class FakeStore:
    def __init__(self, records: dict[str, dict]):
        self.records = records

    async def asearch(self, _ns, limit=10_000):
        return [SimpleNamespace(value=value) for value in self.records.values()][:limit]

    async def aget(self, _ns, key):
        value = self.records.get(key)
        return SimpleNamespace(value=value) if value is not None else None

    async def aput(self, _ns, key, value):
        self.records[key] = value


class FakeCheckpointer:
    async def alist(self, _config=None, limit=None):
        if False:
            yield None
        return

    async def aget_tuple(self, _config):
        return None

    async def aput(self, config, checkpoint, metadata, _writes):
        return {"configurable": {"thread_id": config["configurable"]["thread_id"], "checkpoint_id": "ckpt-1"}}


def _request():
    return SimpleNamespace(scope={"app": True}, app=SimpleNamespace(state=SimpleNamespace()))


def test_can_read_private_thread_only_for_owner():
    record = {"metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE}}

    with patch("app.gateway.ownership.get_workspace_membership", return_value=SimpleNamespace(role="member")):
        assert can_read_thread(record, OWNER) is True
        assert can_read_thread(record, MEMBER) is False


def test_can_read_workspace_thread_for_member_but_not_manage():
    record = {"metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_WORKSPACE}}

    with patch("app.gateway.ownership.get_workspace_membership", return_value=SimpleNamespace(role="member")):
        assert can_read_thread(record, MEMBER) is True
        assert can_manage_thread(record, MEMBER) is False
        assert can_manage_thread(record, OWNER) is True


def test_search_threads_returns_private_owner_and_shared_workspace_threads():
    store = FakeStore(
        {
            "private-owner": {
                "thread_id": "private-owner",
                "status": "idle",
                "created_at": 1,
                "updated_at": 5,
                "metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
                "values": {"title": "Owner Private"},
            },
            "shared-owner": {
                "thread_id": "shared-owner",
                "status": "idle",
                "created_at": 2,
                "updated_at": 6,
                "metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_WORKSPACE},
                "values": {"title": "Owner Shared"},
            },
            "private-other": {
                "thread_id": "private-other",
                "status": "idle",
                "created_at": 3,
                "updated_at": 7,
                "metadata": {THREAD_OWNER_KEY: "member", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
                "values": {"title": "Member Private"},
            },
            "shared-other": {
                "thread_id": "shared-other",
                "status": "idle",
                "created_at": 4,
                "updated_at": 8,
                "metadata": {THREAD_OWNER_KEY: "member", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_WORKSPACE},
                "values": {"title": "Member Shared"},
            },
        }
    )

    with (
        patch("app.gateway.routers.threads.require_user", return_value=OWNER),
        patch("app.gateway.routers.threads.get_store", return_value=store),
        patch("app.gateway.routers.threads.get_checkpointer", return_value=FakeCheckpointer()),
        patch("app.gateway.routers.threads.get_current_workspace_id", return_value="ws-team"),
    ):
        result = asyncio.run(threads_router.search_threads(threads_router.ThreadSearchRequest(), _request()))

    thread_ids = {thread.thread_id for thread in result}
    assert thread_ids == {"private-owner", "shared-owner", "shared-other", "private-other"}


def test_update_thread_visibility_persists_workspace_state():
    store = FakeStore(
        {
            "thread-1": {
                "thread_id": "thread-1",
                "status": "idle",
                "created_at": 1,
                "updated_at": 1,
                "metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
                "values": {},
            }
        }
    )

    async def fake_require_manage(_request, _thread_id):
        return OWNER, store.records["thread-1"]

    async def fake_get_workspace_membership(_user_id, _workspace_id):
        return SimpleNamespace(role="member")

    with (
        patch("app.gateway.routers.threads.require_thread_manage_access", side_effect=fake_require_manage),
        patch("app.gateway.routers.threads.get_store", return_value=store),
        patch("app.gateway.routers.threads.get_checkpointer", return_value=FakeCheckpointer()),
        patch("app.gateway.routers.threads.get_workspace_membership", side_effect=fake_get_workspace_membership),
    ):
        response = asyncio.run(
            threads_router.update_thread_visibility(
                "thread-1",
                threads_router.ThreadVisibilityUpdateRequest(visibility="workspace", workspace_id="ws-team"),
                _request(),
            )
        )

    assert response.metadata[THREAD_VISIBILITY_KEY] == THREAD_VISIBILITY_WORKSPACE
    assert store.records["thread-1"]["metadata"][THREAD_VISIBILITY_KEY] == THREAD_VISIBILITY_WORKSPACE
    assert store.records["thread-1"]["metadata"].get("shared_by_user_id") == "owner"


def test_update_thread_visibility_rejects_personal_workspace_sharing():
    store = FakeStore(
        {
            "thread-1": {
                "thread_id": "thread-1",
                "status": "idle",
                "created_at": 1,
                "updated_at": 1,
                "metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-owner", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
                "values": {},
            }
        }
    )

    async def fake_require_manage(_request, _thread_id):
        return OWNER, store.records["thread-1"]

    with (
        patch("app.gateway.routers.threads.require_thread_manage_access", side_effect=fake_require_manage),
        patch("app.gateway.routers.threads.get_store", return_value=store),
        patch("app.gateway.routers.threads.get_checkpointer", return_value=FakeCheckpointer()),
    ):
        try:
            asyncio.run(
                threads_router.update_thread_visibility(
                    "thread-1",
                    threads_router.ThreadVisibilityUpdateRequest(visibility="workspace"),
                    _request(),
                )
            )
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 422
        else:
            raise AssertionError("Expected personal workspace share to be rejected")


def test_update_thread_title_updates_store_title():
    store = FakeStore(
        {
            "thread-1": {
                "thread_id": "thread-1",
                "status": "idle",
                "created_at": 1,
                "updated_at": 1,
                "metadata": {THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
                "values": {"title": "Old"},
            }
        }
    )

    class TitleCheckpointer(FakeCheckpointer):
        async def aget_tuple(self, _config):
            return SimpleNamespace(
                checkpoint={"channel_values": {"title": "Old"}},
                metadata={THREAD_OWNER_KEY: "owner", THREAD_WORKSPACE_KEY: "ws-team", THREAD_VISIBILITY_KEY: THREAD_VISIBILITY_PRIVATE},
            )

    async def fake_require_manage(_request, _thread_id):
        return OWNER, store.records["thread-1"]

    async def fake_get_workspace_membership(_user_id, _workspace_id):
        return SimpleNamespace(role="member")

    with (
        patch("app.gateway.routers.threads.require_thread_manage_access", side_effect=fake_require_manage),
        patch("app.gateway.routers.threads.get_store", return_value=store),
        patch("app.gateway.routers.threads.get_checkpointer", return_value=FakeCheckpointer()),
        patch("app.gateway.routers.threads.get_workspace_membership", side_effect=fake_get_workspace_membership),
    ):
        response = asyncio.run(
            threads_router.update_thread_title(
                "thread-1",
                threads_router.ThreadTitleUpdateRequest(title="New Title"),
                _request(),
            )
        )

    assert response.values["title"] == "New Title"
    assert store.records["thread-1"]["values"]["title"] == "New Title"
