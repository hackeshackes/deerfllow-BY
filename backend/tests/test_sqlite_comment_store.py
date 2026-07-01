"""SQLite-backed comment store tests."""
from __future__ import annotations

import pytest

from app.gateway.comments.models import CommentSource
from app.gateway.comments.sqlite_store import SqliteCommentStore


@pytest.fixture
def store(tmp_path):
    """A fresh SqliteCommentStore backed by a per-test sqlite file."""
    db = tmp_path / "comments.db"
    return SqliteCommentStore(str(db))


def test_add_then_get_returns_same_comment(store):
    c = store.add("t-1", "alice", "hello")
    assert c.id.startswith("c-")
    got = store.get(c.id)
    assert got is not None
    assert got.author_id == "alice"
    assert got.text == "hello"
    assert got.thread_id == "t-1"


def test_list_for_thread_filters_correctly(store):
    store.add("t-1", "alice", "first")
    store.add("t-2", "bob", "different thread")
    store.add("t-1", "carol", "second")

    items = store.list_for_thread("t-1")
    assert len(items) == 2
    assert all(c.thread_id == "t-1" for c in items)


def test_list_for_thread_is_newest_first(store):
    store.add("t-1", "alice", "first")
    store.add("t-1", "bob", "second")
    store.add("t-1", "carol", "third")

    items = store.list_for_thread("t-1")
    assert items[0].text == "third"
    assert items[2].text == "first"


def test_list_for_thread_respects_limit(store):
    for i in range(5):
        store.add("t-1", "u", f"c-{i}")
    assert len(store.list_for_thread("t-1", limit=3)) == 3


def test_delete_returns_true_then_false(store):
    c = store.add("t-1", "alice", "x")
    assert store.delete(c.id) is True
    assert store.delete(c.id) is False
    assert store.get(c.id) is None


def test_persistence_across_instances(tmp_path):
    """Two stores pointing at the same file should see each other's writes."""
    db = str(tmp_path / "shared.db")
    a = SqliteCommentStore(db)
    a.add("t-1", "alice", "from a")
    b = SqliteCommentStore(db)
    items = b.list_for_thread("t-1")
    assert len(items) == 1
    assert items[0].text == "from a"


def test_factory_memory_is_default(monkeypatch):
    monkeypatch.delenv("MICX_COMMENTS_STORE", raising=False)
    from app.gateway.comments.service import get_comment_store
    from app.gateway.comments.service import InMemoryCommentStore

    assert isinstance(get_comment_store(), InMemoryCommentStore)


def test_factory_sqlite_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MICX_COMMENTS_STORE", "sqlite")
    db = tmp_path / "test.db"
    monkeypatch.setenv("MICX_COMMENTS_DB", str(db))
    from app.gateway.comments.service import get_comment_store

    store = get_comment_store()
    assert isinstance(store, SqliteCommentStore)
    # Confirm it's the SQLite-backed variant by adding and reading back.
    c = store.add("t-1", "alice", "persisted")
    assert store.get(c.id) is not None


def test_source_default_is_user(store):
    c = store.add("t-1", "alice", "x")
    assert c.source == CommentSource.USER
    c2 = store.add("t-1", "agent-bot", "x", source=CommentSource.AGENT)
    assert c2.source == CommentSource.AGENT
