"""Async batched audit event writer.

Events are buffered in-memory and flushed to SQLite in batches.
Production: replace SQLite with PostgreSQL append-only table.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from .models import AuditEvent


class AuditWriter:
    def __init__(self, db_path: str | None = None, batch_size: int = 100, flush_interval: float = 1.0):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "identity.db")
        self._db_path = db_path
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: list[AuditEvent] = []
        # threading.Lock so the writer is safe to share across the event
        # loops used by TestClient (anyio portal) and the pytest-asyncio
        # test loop. asyncio.Lock would bind to whichever loop creates it
        # and fail when re-entered from a different loop.
        self._lock = threading.Lock()
        self._closed = False
        self._init_db()
        self._task: asyncio.Task | None = None

    def _init_db(self):
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    occurred_at TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    workspace_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    metadata_json TEXT,
                    success INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actor_time ON audit_events(actor_id, occurred_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workspace_time ON audit_events(workspace_id, occurred_at)")

    async def write(self, event: AuditEvent) -> None:
        with self._lock:
            self._buffer.append(event)
            should_flush = len(self._buffer) >= self._batch_size
        if should_flush:
            await self.flush()

    async def _flush_locked(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            events = self._buffer[:]
            self._buffer = []
        await asyncio.get_event_loop().run_in_executor(None, self._insert_batch, events)

    def _insert_batch(self, events: list[AuditEvent]) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self._db_path) as conn:
            for e in events:
                e.occurred_at = e.occurred_at or now
                conn.execute(
                    """INSERT OR REPLACE INTO audit_events
                       (id, occurred_at, actor_id, actor_type, action, resource_type,
                        resource_id, workspace_id, ip_address, user_agent, metadata_json, success)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (e.id, e.occurred_at, e.actor_id, e.actor_type.value, e.action, e.resource_type,
                     e.resource_id, e.workspace_id, e.ip_address, e.user_agent,
                     json.dumps(e.metadata), 1 if e.success else 0),
                )

    async def flush(self) -> None:
        await self._flush_locked()

    async def close(self) -> None:
        await self.flush()
        self._closed = True

    async def query(
        self,
        actor_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        await self.flush()
        clauses = []
        params: list = []
        if actor_id:
            clauses.append("actor_id = ?"); params.append(actor_id)
        if workspace_id:
            clauses.append("workspace_id = ?"); params.append(workspace_id)
        if action:
            clauses.append("action = ?"); params.append(action)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM audit_events {where} ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row) -> AuditEvent:
        from .models import ActorType
        return AuditEvent(
            id=row[0], occurred_at=row[1], actor_id=row[2], actor_type=ActorType(row[3]),
            action=row[4], resource_type=row[5], resource_id=row[6], workspace_id=row[7],
            ip_address=row[8], user_agent=row[9], metadata=json.loads(row[10] or "{}"),
            success=bool(row[11]),
        )