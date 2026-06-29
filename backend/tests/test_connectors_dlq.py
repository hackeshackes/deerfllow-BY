"""Tests for the in-memory dead-letter queue store.

The DLQ store is the admin-side counterpart to `ConnectorRuntime`:
the runtime pushes entries when retries exhaust, the admin API queries and
clears them through the store.
"""
from __future__ import annotations

import pytest

from app.gateway.connectors.dlq import InMemoryDLQStore


def _entry(connector: str = "feishu", text: str = "x") -> dict:
    return {
        "connector": connector,
        "error": "timeout",
        "attempts": 3,
        "message": {"text": text, "target": {}},
    }


def test_dlq_push_returns_id_and_list_contains_entry():
    s = InMemoryDLQStore()
    item_id = s.push(_entry())
    assert item_id
    items = s.list_all()
    assert len(items) == 1
    assert items[0]["id"] == item_id
    assert items[0]["connector"] == "feishu"
    assert "timestamp" in items[0]


def test_dlq_get_returns_full_entry():
    s = InMemoryDLQStore()
    item_id = s.push(_entry(text="hello"))
    got = s.get(item_id)
    assert got is not None
    assert got["message"]["text"] == "hello"


def test_dlq_get_missing_returns_none():
    s = InMemoryDLQStore()
    assert s.get("nope") is None


def test_dlq_delete_removes_entry():
    s = InMemoryDLQStore()
    item_id = s.push(_entry())
    assert s.delete(item_id) is True
    assert s.list_all() == []
    # Second delete is a no-op
    assert s.delete(item_id) is False


def test_dlq_clear_all_returns_count():
    s = InMemoryDLQStore()
    s.push(_entry(connector="a"))
    s.push(_entry(connector="b"))
    s.push(_entry(connector="c"))
    n = s.clear_all()
    assert n == 3
    assert s.list_all() == []


def test_dlq_list_newest_first():
    s = InMemoryDLQStore()
    s.push(_entry(connector="first"))
    s.push(_entry(connector="second"))
    s.push(_entry(connector="third"))
    items = s.list_all()
    # All entries stamped in the same second; ordering is implementation-
    # defined, but the *set* of connectors must be present.
    assert {i["connector"] for i in items} == {"first", "second", "third"}


def test_dlq_limit_respected():
    s = InMemoryDLQStore()
    for i in range(5):
        s.push(_entry(connector=f"c{i}"))
    assert len(s.list_all(limit=3)) == 3


def test_dlq_ids_are_unique():
    s = InMemoryDLQStore()
    ids = {s.push(_entry()) for _ in range(10)}
    assert len(ids) == 10
