"""Dead-letter queue storage — in-memory implementation.

The runtime emits `DLQEntry` dataclasses (see `runtime.py`); the admin-facing
endpoints in `routers/connectors.py` talk to `InMemoryDLQStore` for list /
delete / clear. The store is intentionally trivial — the production story
will replace it with a SQLite/Postgres-backed implementation, but the API
shape stays the same so callers don't need to change.
"""
from __future__ import annotations

import time
import uuid


class InMemoryDLQStore:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    # --------------------------------------------------------------------- write
    def push(self, entry: dict) -> str:
        """Store a DLQ entry. Returns the assigned id.

        The store stamps `id` and `timestamp` if not already present; otherwise
        caller's value is preserved.
        """
        item_id = str(entry.get("id") or uuid.uuid4())
        stamped = {
            "id": item_id,
            "timestamp": entry.get("timestamp")
            or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **{k: v for k, v in entry.items() if k not in ("id", "timestamp")},
        }
        self._items[item_id] = stamped
        return item_id

    # ---------------------------------------------------------------------- read
    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def list_all(self, limit: int | None = None) -> list[dict]:
        items = sorted(
            self._items.values(), key=lambda x: x.get("timestamp", ""), reverse=True
        )
        if limit is not None:
            return items[:limit]
        return items

    # -------------------------------------------------------------------- delete
    def delete(self, item_id: str) -> bool:
        return self._items.pop(item_id, None) is not None

    def clear_all(self) -> int:
        n = len(self._items)
        self._items.clear()
        return n
