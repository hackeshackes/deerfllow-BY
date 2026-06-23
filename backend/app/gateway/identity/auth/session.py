"""Session storage with TTL. In-memory implementation; production should
use Redis (replace with a Redis-backed store implementing the same interface).
"""
from __future__ import annotations

import time
from typing import Any, Protocol


class SessionStore(Protocol):
    async def create(self, session_id: str, data: dict, ttl_seconds: int) -> None: ...
    async def get(self, session_id: str) -> dict[str, Any] | None: ...
    async def delete(self, session_id: str) -> None: ...


class InMemorySessionStore:
    """Process-local session store. Replace with Redis in production."""

    def __init__(self):
        self._store: dict[str, tuple[dict, float]] = {}

    async def create(self, session_id: str, data: dict, ttl_seconds: int) -> None:
        expires_at = time.time() + ttl_seconds
        self._store[session_id] = (data, expires_at)

    async def get(self, session_id: str) -> dict[str, Any] | None:
        entry = self._store.get(session_id)
        if not entry:
            return None
        data, expires_at = entry
        if time.time() > expires_at:
            del self._store[session_id]
            return None
        return data

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)