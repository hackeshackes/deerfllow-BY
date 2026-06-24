import pytest
from app.gateway.identity.scim.sync import SCIMSyncService, InMemoryUserStore
from app.gateway.identity.scim.client import SCIMClient
from app.gateway.identity.scim.models import SCIMUser


@pytest.fixture
def store():
    return InMemoryUserStore()


@pytest.fixture
def fake_client():
    return SCIMClient(base_url="https://x/scim/v2", bearer_token="t")


@pytest.mark.asyncio
async def test_sync_creates_new_users(store, fake_client, monkeypatch):
    async def fake_list_users():
        return [
            SCIMUser(id="u-1", userName="alice", emails=["a@x"], display_name="Alice", groups=["eng"]),
            SCIMUser(id="u-2", userName="bob", emails=["b@x"], display_name="Bob", groups=[]),
        ]

    monkeypatch.setattr(fake_client, "list_users", fake_list_users)

    svc = SCIMSyncService(client=fake_client, store=store)
    result = await svc.sync_users()
    assert result.created == 2
    assert result.updated == 0
    assert await store.count() == 2


@pytest.mark.asyncio
async def test_sync_updates_existing_users(store, fake_client, monkeypatch):
    await store.upsert({"id": "u-1", "email": "a@x", "name": "AliceOld", "active": True, "groups": []})

    async def fake_list_users():
        return [
            SCIMUser(id="u-1", userName="alice", emails=["a@x"], display_name="AliceNew", groups=["eng"]),
        ]

    monkeypatch.setattr(fake_client, "list_users", fake_list_users)

    svc = SCIMSyncService(client=fake_client, store=store)
    result = await svc.sync_users()
    assert result.created == 0
    assert result.updated == 1
    u = await store.get("u-1")
    assert u["name"] == "AliceNew"


@pytest.mark.asyncio
async def test_sync_deactivates_removed_users(store, fake_client, monkeypatch):
    await store.upsert({"id": "u-old", "email": "o@x", "name": "Old", "active": True, "groups": []})

    async def fake_list_users():
        return []  # no users in IdP

    monkeypatch.setattr(fake_client, "list_users", fake_list_users)

    svc = SCIMSyncService(client=fake_client, store=store, deactivate_missing=True)
    result = await svc.sync_users()
    assert result.deactivated == 1
    u = await store.get("u-old")
    assert u["active"] is False