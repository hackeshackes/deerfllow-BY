"""End-to-end: SCIM client → sync service → in-memory store."""
import pytest
from app.gateway.identity.scim.client import SCIMClient
from app.gateway.identity.scim.sync import SCIMSyncService, InMemoryUserStore
from app.gateway.identity.scim.models import SCIMUser


@pytest.mark.asyncio
async def test_full_sync_flow(monkeypatch):
    client = SCIMClient(base_url="https://x", bearer_token="t")
    store = InMemoryUserStore()

    async def fake_fetch():
        return [
            SCIMUser(id="u1", userName="alice", emails=["a@x"], display_name="A", groups=[]),
        ]

    monkeypatch.setattr(client, "list_users", fake_fetch)

    svc = SCIMSyncService(client=client, store=store)
    result = await svc.sync_users()
    assert result.created == 1
    assert await store.count() == 1