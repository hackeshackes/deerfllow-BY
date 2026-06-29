"""Tests for the SQLite-backed DLQ store."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.gateway.connectors.base import ConnectorMessage
from app.gateway.connectors.dlq import InMemoryDLQStore
from app.gateway.connectors.persistence.sqlite_dlq import (
    SqliteDLQStore,
    flush_to_sqlite,
)
from app.gateway.connectors.runtime import DLQEntry


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "dlq.db"


def _make_entry(connector: str = "feishu", text: str = "hello") -> DLQEntry:
    return DLQEntry(
        connector=connector,
        message=ConnectorMessage(text=text, target={"chat_id": "c1"}),
        last_error="timeout",
        attempts=3,
    )


def test_sqlite_dlq_push_and_list(db_path: Path):
    store = SqliteDLQStore(db_path)
    try:
        store.push(
            {
                "connector": "feishu",
                "error": "timeout",
                "attempts": 3,
                "message": {"text": "hi", "target": {}},
            }
        )
        items = store.list_all()
        assert len(items) == 1
        assert items[0]["connector"] == "feishu"
        assert items[0]["error"] == "timeout"
        assert items[0]["message"]["text"] == "hi"
        assert "timestamp" in items[0]
    finally:
        store.close()


def test_sqlite_dlq_persists_across_instances(db_path: Path):
    first = SqliteDLQStore(db_path)
    first.push({"connector": "x", "error": "y", "attempts": 1, "message": {}})
    first.close()
    second = SqliteDLQStore(db_path)
    items = second.list_all()
    assert len(items) == 1
    assert items[0]["connector"] == "x"
    second.close()


def test_sqlite_dlq_delete_returns_false_for_missing(db_path: Path):
    store = SqliteDLQStore(db_path)
    try:
        assert store.delete("nope") is False
    finally:
        store.close()


def test_sqlite_dlq_clear_all_returns_count(db_path: Path):
    store = SqliteDLQStore(db_path)
    try:
        for i in range(3):
            store.push({"connector": f"c{i}", "error": "e", "attempts": 1, "message": {}})
        n = store.clear_all()
        assert n == 3
        assert store.list_all() == []
    finally:
        store.close()


def test_sqlite_dlq_ids_are_unique(db_path: Path):
    store = SqliteDLQStore(db_path)
    try:
        ids = set()
        for i in range(10):
            ids.add(
                store.push(
                    {"connector": f"c{i}", "error": "e", "attempts": 1, "message": {}}
                )
            )
        assert len(ids) == 10
    finally:
        store.close()


def test_flush_to_sqlite_clears_source(db_path: Path):
    mem = InMemoryDLQStore()
    # The runtime calls `mem.push({...dict...})`, not `mem.push(DLQEntry)`.
    # Replicate that contract.
    msg_a = _make_entry("feishu", "msg-a").message
    msg_b = _make_entry("dingtalk", "msg-b").message
    mem.push({
        "connector": "feishu",
        "error": "timeout",
        "attempts": 3,
        "message": {"text": msg_a.text, "target": msg_a.target},
    })
    mem.push({
        "connector": "dingtalk",
        "error": "down",
        "attempts": 2,
        "message": {"text": msg_b.text, "target": msg_b.target},
    })
    sq = SqliteDLQStore(db_path)
    try:
        n = flush_to_sqlite(mem, sq)
        assert n == 2
        assert mem.list_all() == []
        items = sq.list_all()
        assert len(items) == 2
        assert {i["connector"] for i in items} == {"feishu", "dingtalk"}
    finally:
        sq.close()


def test_flush_to_sqlite_round_trips_message_payload(db_path: Path):
    mem = InMemoryDLQStore()
    mem.push({
        "connector": "feishu",
        "error": "rate limited",
        "attempts": 2,
        "message": {
            "text": "hello",
            "target": {"chat_id": "c1", "user_id": "u1"},
            "attachments": [{"name": "f.txt", "size": 12}],
            "metadata": {"key": "value"},
        },
    })
    sq = SqliteDLQStore(db_path)
    try:
        flush_to_sqlite(mem, sq)
        items = sq.list_all()
        assert items[0]["message"]["text"] == "hello"
        assert items[0]["message"]["target"]["chat_id"] == "c1"
        assert items[0]["message"]["metadata"] == {"key": "value"}
    finally:
        sq.close()
