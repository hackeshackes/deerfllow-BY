"""SQLite-backed DLQ store.

Production use: write DLQ entries to a file-backed SQLite DB so they survive
process restarts. The runtime keeps the in-memory `InMemoryDLQStore` for
the hot path; on `flush_to_sqlite()` it bulk-inserts pending entries and
removes them from memory.

Concurrency: a process-level `threading.Lock` serializes writes. SQLite's
own locking handles cross-process concurrency at the file level.

A separate read API (`SqliteDLQStore`) is provided for the admin router
to load historical entries that aren't in the in-memory cache.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from ..dlq import InMemoryDLQStore


class SqliteDLQStore:
    """Append-only DLQ persistence backed by SQLite.

    This is a simple, dependency-free implementation. Production may swap
    in a real DB connection (e.g. asyncpg + Postgres) without changing the
    connector runtime — the interface here matches `InMemoryDLQStore`.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS dlq_entries (
        id TEXT PRIMARY KEY,
        connector TEXT NOT NULL,
        last_error TEXT NOT NULL,
        attempts INTEGER NOT NULL,
        message_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_dlq_created_at
        ON dlq_entries(created_at DESC);
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # check_same_thread=False so the runtime (async, possibly on a
        # worker thread) and the admin router (sync) can both use the
        # same connection. SQLite handles its own cross-process locking.
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def push(self, entry: dict) -> str:
        """Persist one DLQ entry; returns its id (auto-assigned if missing)."""
        import uuid

        entry_id = entry.get("id") or f"dlq-{uuid.uuid4().hex[:12]}"
        stamped = {
            "id": entry_id,
            "connector": entry["connector"],
            "last_error": entry.get("error", ""),
            "attempts": int(entry.get("attempts", 0)),
            "message_json": json.dumps(entry.get("message") or {}),
            "timestamp": entry.get("timestamp")
            or _now_iso(),
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO dlq_entries
                    (id, connector, last_error, attempts, message_json, created_at)
                VALUES (:id, :connector, :last_error, :attempts, :message_json, :timestamp)
                """,
                stamped,
            )
            self._conn.commit()
        return entry_id

    def list_all(self, limit: int | None = None) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM dlq_entries ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        items = [
            {
                "id": r["id"],
                "connector": r["connector"],
                "error": r["last_error"],
                "attempts": r["attempts"],
                "message": json.loads(r["message_json"]),
                "timestamp": r["created_at"],
            }
            for r in rows
        ]
        return items[:limit] if limit is not None else items

    def delete(self, item_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM dlq_entries WHERE id = ?", (item_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0

    def clear_all(self) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM dlq_entries")
            self._conn.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _now_iso() -> str:
    """Return the current UTC time in ISO 8601 with second precision."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def flush_to_sqlite(
    source: InMemoryDLQStore,
    dest: SqliteDLQStore,
) -> int:
    """Bulk-persist all entries from `source` into `dest` and clear `source`.

    Returns the number of entries flushed. Safe to call from the async
    runtime — the underlying `push` uses stdlib sqlite3 which blocks the
    event loop briefly; for production swap to aiosqlite.
    """
    items = source.list_all()
    n = 0
    for entry in items:
        # `InMemoryDLQStore.list_all()` returns dicts that mirror the
        # payload we want to persist — just re-stamp them with the
        # DB-friendly shape (id, error, attempts already aligned).
        msg = entry.get("message") or {}
        dest.push(
            {
                "id": entry["id"],
                "connector": entry["connector"],
                "error": entry.get("error", ""),
                "attempts": int(entry.get("attempts", 0)),
                "message": {
                    "text": msg.get("text", ""),
                    "target": msg.get("target", {}),
                    "attachments": msg.get("attachments", []),
                    "metadata": msg.get("metadata", {}),
                },
                "timestamp": entry.get("timestamp"),
            }
        )
        n += 1
    if n:
        source.clear_all()
    return n
