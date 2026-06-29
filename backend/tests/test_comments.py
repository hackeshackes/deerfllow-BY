"""Tests for the comments service."""
from __future__ import annotations

import pytest

from app.gateway.comments.models import CommentSource
from app.gateway.comments.service import (
    InMemoryCommentStore,
    extract_mentions,
)


def test_extract_mentions_single():
    assert extract_mentions("hi @alice") == ["alice"]


def test_extract_mentions_multiple():
    assert extract_mentions("@alice and @bob, also @alice") == ["alice", "bob"]


def test_extract_mentions_empty():
    assert extract_mentions("no mentions here") == []


def test_extract_mentions_ignores_emails():
    """An email `alice@acme.com` is not a mention — only @ at the start."""
    assert extract_mentions("contact alice@acme.com") == []


def test_extract_mentions_respects_length_cap():
    """@verylonghandlenamethatdoesnotfit is not a mention (>30 chars)."""
    long = "a" * 31
    assert extract_mentions(f"@{long}") == []


def test_store_add_returns_comment_with_id():
    s = InMemoryCommentStore()
    c = s.add("t-1", "alice", "hello world")
    assert c.id.startswith("c-")
    assert c.thread_id == "t-1"
    assert c.author_id == "alice"
    assert c.text == "hello world"
    assert c.mentioned_user_ids == []


def test_store_add_extracts_mentions():
    s = InMemoryCommentStore()
    c = s.add("t-1", "alice", "cc @bob and @carol")
    assert c.mentioned_user_ids == ["bob", "carol"]


def test_store_list_for_thread_returns_thread_only():
    s = InMemoryCommentStore()
    s.add("t-1", "alice", "first")
    s.add("t-2", "bob", "different thread")
    s.add("t-1", "carol", "second")
    items = s.list_for_thread("t-1")
    assert len(items) == 2
    assert all(c.thread_id == "t-1" for c in items)


def test_store_list_for_thread_newest_first():
    import time
    s = InMemoryCommentStore()
    s.add("t-1", "alice", "first")
    time.sleep(0.01)  # ensure distinct created_at timestamps
    s.add("t-1", "bob", "second")
    time.sleep(0.01)
    s.add("t-1", "carol", "third")
    items = s.list_for_thread("t-1")
    assert items[0].text == "third"
    assert items[2].text == "first"


def test_store_list_respects_limit():
    s = InMemoryCommentStore()
    for i in range(5):
        s.add("t-1", "u", f"c-{i}")
    assert len(s.list_for_thread("t-1", limit=3)) == 3


def test_store_delete_returns_true_then_false():
    s = InMemoryCommentStore()
    c = s.add("t-1", "alice", "x")
    assert s.delete(c.id) is True
    assert s.delete(c.id) is False
    assert s.get(c.id) is None


def test_comment_with_parent():
    s = InMemoryCommentStore()
    parent = s.add("t-1", "alice", "root")
    reply = s.add("t-1", "bob", "@alice +1", parent_comment_id=parent.id)
    assert reply.parent_comment_id == parent.id


def test_source_default_is_user():
    s = InMemoryCommentStore()
    c = s.add("t-1", "alice", "x")
    assert c.source == CommentSource.USER
    c2 = s.add("t-1", "agent-bot", "x", source=CommentSource.AGENT)
    assert c2.source == CommentSource.AGENT
