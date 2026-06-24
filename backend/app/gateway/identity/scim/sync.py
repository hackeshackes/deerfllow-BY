"""SCIM sync service: pulls Users/Groups from IdP and reconciles with internal store."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .client import SCIMClient
from .mappings import scim_user_to_internal


class UserStore(Protocol):
    async def upsert(self, user: dict) -> None: ...
    async def get(self, user_id: str) -> dict | None: ...
    async def list_all_ids(self) -> list[str]: ...
    async def count(self) -> int: ...


class InMemoryUserStore:
    def __init__(self):
        self._users: dict[str, dict] = {}

    async def upsert(self, user: dict) -> None:
        self._users[user["id"]] = user

    async def get(self, user_id: str) -> dict | None:
        return self._users.get(user_id)

    async def list_all_ids(self) -> list[str]:
        return list(self._users.keys())

    async def count(self) -> int:
        return len(self._users)


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    deactivated: int = 0
    errors: list[str] = field(default_factory=list)


class SCIMSyncService:
    def __init__(
        self,
        client: SCIMClient,
        store: UserStore,
        deactivate_missing: bool = True,
    ):
        self._client = client
        self._store = store
        self._deactivate_missing = deactivate_missing

    async def sync_users(self) -> SyncResult:
        result = SyncResult()
        try:
            scim_users = await self._client.list_users()
        except Exception as e:
            result.errors.append(f"fetch failed: {e}")
            return result

        seen_ids: set[str] = set()
        for su in scim_users:
            internal = scim_user_to_internal(su)
            existing = await self._store.get(internal["id"])
            if existing is None:
                result.created += 1
            else:
                result.updated += 1
            await self._store.upsert(internal)
            seen_ids.add(internal["id"])

        if self._deactivate_missing:
            all_ids = await self._store.list_all_ids()
            for uid in all_ids:
                if uid not in seen_ids:
                    u = await self._store.get(uid)
                    if u and u.get("active"):
                        u["active"] = False
                        await self._store.upsert(u)
                        result.deactivated += 1

        return result