import pytest
import asyncio
from app.gateway.identity.auth.session import InMemorySessionStore

@pytest.mark.asyncio
async def test_session_create_and_get():
    store = InMemorySessionStore()
    await store.create("sess-1", {"user_id": "u-1"}, ttl_seconds=60)
    s = await store.get("sess-1")
    assert s is not None
    assert s["user_id"] == "u-1"

@pytest.mark.asyncio
async def test_session_expires():
    store = InMemorySessionStore()
    await store.create("sess-1", {"user_id": "u-1"}, ttl_seconds=0)
    # With ttl=0, expiry is already past
    s = await store.get("sess-1")
    assert s is None

@pytest.mark.asyncio
async def test_session_delete():
    store = InMemorySessionStore()
    await store.create("sess-1", {"x": 1}, ttl_seconds=60)
    await store.delete("sess-1")
    assert await store.get("sess-1") is None

@pytest.mark.asyncio
async def test_session_returns_none_if_missing():
    store = InMemorySessionStore()
    assert await store.get("nonexistent") is None