"""Comment service — CRUD + @mention parsing.

In v1.5.8 the service is in-memory and the @mention fan-out is a
no-op (real delivery requires a NotificationChannel implementation,
which is deferred). The CRUD contract is what the API and the
real-time UI consume.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .models import Comment, CommentSource


# Matches `@handle` tokens where:
#   - the `@` is at the start of the string OR preceded by a non-word char
#   - the handle is 1-30 word characters
#   - the handle is NOT followed by another word char (so a 31-character
#     run doesn't have the first 30 chars mis-classified as a handle)
# The negative-lookbehind `(?<!\w)` excludes email addresses
# (e.g. `alice@acme.com` is not a mention because the `@` is preceded
# by `e`).
_MENTION_RE = re.compile(r"(?<!\w)@(\w{1,30})(?!\w)")


def extract_mentions(text: str) -> list[str]:
    """Return the deduped list of @handles found in `text`.

    Notes:
    - Email addresses like `alice@acme.com` are NOT treated as mentions.
    - Handles are limited to 1-30 word characters.
    """
    handles = _MENTION_RE.findall(text)
    return sorted(set(handles))


class InMemoryCommentStore:
    def __init__(self) -> None:
        self._items: dict[str, Comment] = {}

    def add(
        self,
        thread_id: str,
        author_id: str,
        text: str,
        source: CommentSource = CommentSource.USER,
        parent_comment_id: str | None = None,
    ) -> Comment:
        cid = f"c-{uuid.uuid4().hex[:12]}"
        mentioned = extract_mentions(text)
        comment = Comment(
            id=cid,
            thread_id=thread_id,
            author_id=author_id,
            text=text,
            source=source,
            parent_comment_id=parent_comment_id,
            mentioned_user_ids=mentioned,
            created_at=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
        )
        self._items[cid] = comment
        return comment

    def get(self, comment_id: str) -> Comment | None:
        return self._items.get(comment_id)

    def list_for_thread(
        self, thread_id: str, limit: int = 100
    ) -> list[Comment]:
        items = [c for c in self._items.values() if c.thread_id == thread_id]
        # Newest first; deterministic when created_at ties (uuid secondary).
        items.sort(key=lambda c: (c.created_at, c.id), reverse=True)
        return items[:limit]

    def delete(self, comment_id: str) -> bool:
        return self._items.pop(comment_id, None) is not None


def get_comment_store():
    """Resolve the comment store based on the MICX_COMMENTS_STORE env.

    Returns ``InMemoryCommentStore`` by default (v1.5.8 behaviour, dev
    cold-start friendly). Set ``MICX_COMMENTS_STORE=sqlite`` to switch
    to ``SqliteCommentStore``; the DB path defaults to
    ``backend/.deer-flow/comments.db`` and can be overridden by
    ``MICX_COMMENTS_DB``.

    Reads env vars fresh on each invocation so test fixtures that set
    the env mid-process pick up the right backend.
    """
    import os

    backend = os.environ.get("MICX_COMMENTS_STORE", "memory").lower()
    if backend == "sqlite":
        from .sqlite_store import SqliteCommentStore

        db_path = os.environ.get("MICX_COMMENTS_DB", ".deer-flow/comments.db")
        return SqliteCommentStore(db_path)
    return InMemoryCommentStore()
