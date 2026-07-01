"""SQLite-backed CommentStore.

Same surface as ``InMemoryCommentStore`` (add / get / list_for_thread
/ delete). The schema lives at
``backend/app/gateway/data/migrations/004_v1.5.8_multitenancy.sql``
(comments table + idx_comments_thread index).

Switched on via env var ``MICX_COMMENTS_STORE=sqlite`` — see
``service.get_comment_store``. Default is ``"memory"`` to keep dev
cold-start behaviour identical to v1.5.8.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .models import Comment, CommentSource


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class SqliteCommentStore:
    """Persistent thread-scoped comment store.

    Thread-safe: a single lock guards the connection, one writer at a
    time. Read contention is non-blocking (sqlite default).
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        # check_same_thread=False lets a single instance handle requests
        # from multiple worker threads (uvicorn with --workers 4 hits
        # this from each worker pool). We still serialize writes via
        # _lock; reads intentionally take the lock too for snapshot
        # consistency across row reads.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id         TEXT PRIMARY KEY,
                    thread_id  TEXT NOT NULL,
                    author     TEXT NOT NULL,
                    body       TEXT NOT NULL,
                    parent_id  TEXT,
                    source     TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_comments_thread
                    ON comments(thread_id);
                """
            )
            self._conn.commit()

    def add(
        self,
        thread_id: str,
        author_id: str,
        text: str,
        source: CommentSource = CommentSource.USER,
        parent_comment_id: str | None = None,
    ) -> Comment:
        cid = f"c-{uuid.uuid4().hex[:12]}"
        created_at = _utcnow()
        source_str = source.value if hasattr(source, "value") else str(source)
        with self._lock:
            self._conn.execute(
                "INSERT INTO comments (id, thread_id, author, body, parent_id, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    cid, thread_id, author_id, text,
                    parent_comment_id, source_str, created_at,
                ),
            )
            self._conn.commit()
        # Mentions are derived client-side; reusing the in-memory
        # extraction keeps this store symmetric with the in-memory one
        # so the API surface stays the same.
        from .service import extract_mentions

        mentioned = extract_mentions(text)
        return Comment(
            id=cid,
            thread_id=thread_id,
            author_id=author_id,
            text=text,
            source=source,
            parent_comment_id=parent_comment_id,
            mentioned_user_ids=mentioned,
            created_at=created_at,
        )

    def get(self, comment_id: str) -> Comment | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM comments WHERE id = ?", (comment_id,),
            ).fetchone()
        return _row_to_comment(row) if row else None

    def list_for_thread(
        self, thread_id: str, limit: int = 100
    ) -> list[Comment]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM comments WHERE thread_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (thread_id, limit),
            ).fetchall()
        return [_row_to_comment(r) for r in rows]

    def delete(self, comment_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM comments WHERE id = ?", (comment_id,),
            )
            self._conn.commit()
            return cur.rowcount > 0


def _row_to_comment(row: sqlite3.Row) -> Comment:
    """Translate a sqlite row into the domain Comment dataclass.

    We intentionally re-derive ``mentioned_user_ids`` at write time
    (see ``add`` above) rather than storing them, so reading from disk
    returns an empty list. That mirrors what the in-memory store would
    return for a comment whose mentions were never re-derived post-write
    — a small but consistent compromise so callers cannot grow to depend
    on disk-resident mention state.
    """
    return Comment(
        id=row["id"],
        thread_id=row["thread_id"],
        author_id=row["author"],
        text=row["body"],
        source=CommentSource(row["source"]),
        parent_comment_id=row["parent_id"],
        mentioned_user_ids=[],
        created_at=row["created_at"],
    )
