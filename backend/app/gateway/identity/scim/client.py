"""SCIM 2.0 client for fetching Users and Groups from an IdP."""
from __future__ import annotations

import httpx

from .models import SCIMGroup, SCIMUser


class SCIMClient:
    def __init__(self, base_url: str, bearer_token: str, timeout: float = 30.0):
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/scim+json",
        }
        self._timeout = timeout

    async def list_users(self) -> list[SCIMUser]:
        """List all users (no pagination; IdP-side limited to 1000)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/Users", headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
        return [SCIMUser.from_dict(r) for r in data.get("Resources", [])]

    async def list_groups(self) -> list[SCIMGroup]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/Groups", headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
        return [SCIMGroup.from_dict(r) for r in data.get("Resources", [])]

    async def list_users_paginated(self, count_per_page: int = 100) -> list[SCIMUser]:
        """Fetch all users via SCIM pagination."""
        all_users: list[SCIMUser] = []
        start_index = 1
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                resp = await client.get(
                    f"{self._base}/Users",
                    headers=self._headers,
                    params={"startIndex": start_index, "count": count_per_page},
                )
                resp.raise_for_status()
                data = resp.json()
                resources = data.get("Resources", [])
                all_users.extend(SCIMUser.from_dict(r) for r in resources)
                if len(resources) < count_per_page:
                    break
                start_index += count_per_page
        return all_users