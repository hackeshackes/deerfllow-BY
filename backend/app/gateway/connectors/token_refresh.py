"""Token refresh helper for IM connectors.

A `CachedToken` wraps an async fetcher and:
- Caches the value until `ttl_seconds` elapses
- Uses single-flight (concurrent in-flight fetches are coalesced) to avoid
  thundering herd when many requests see the same expired token at once
- Lets callers force a refresh on demand via `invalidate()` (e.g. when
  a 401 from the upstream signals the token has been revoked server-side)

The fetcher is expected to raise on failure; the caller decides how to
handle errors (the IM connectors translate them into `ConnectorResponse`
with `success=False`).
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

# A fetcher takes no arguments and returns the new token string.
TokenFetcher = Callable[[], Awaitable[str]]


class CachedToken:
    """Async-safe token cache with TTL and single-flight refresh."""

    def __init__(self, fetcher: TokenFetcher, ttl_seconds: float) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self._fetcher = fetcher
        self._ttl = ttl_seconds
        self._value: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def value(self) -> str | None:
        """Read the cached value without fetching. Returns None if not loaded."""
        return self._value

    def invalidate(self) -> None:
        """Force the next `get()` to refetch."""
        self._value = None
        self._expires_at = 0.0

    def _is_expired(self) -> bool:
        return time.monotonic() >= self._expires_at

    async def get(self) -> str:
        """Return a valid token, refreshing if needed.

        Concurrent calls during an in-flight refresh share the same fetch
        (single-flight). After the in-flight fetch completes, a follow-up
        `get()` reuses the result without refetching.

        Implementation: serialize the slow path on a lock. The first caller
        to acquire the lock after expiry performs the fetch; followers
        re-acquire the lock and observe the fresh value.
        """
        # Fast path: token is loaded and not expired.
        if self._value is not None and not self._is_expired():
            return self._value

        # Slow path: serialize on the lock.
        async with self._lock:
            if self._value is not None and not self._is_expired():
                return self._value
            value = await self._fetcher()
            self._value = value
            self._expires_at = time.monotonic() + self._ttl
            return value
