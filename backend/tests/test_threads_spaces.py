"""Tests for the extended Thread model (v1.5.5)."""
from __future__ import annotations

import pytest

from app.gateway.threads.models import SpaceType, Thread, ThreadSource


def test_thread_defaults():
    t = Thread(id="t-1", title="x", user_id="u-1", workspace_id="w-1")
    assert t.space_type == SpaceType.PERSONAL
    assert t.source == ThreadSource.MANUAL
    assert t.published_from_thread_id is None


def test_thread_with_publication_link():
    t = Thread(
        id="t-2",
        title="y",
        user_id="u-1",
        workspace_id="w-1",
        space_type=SpaceType.WORKSPACE,
        source=ThreadSource.AUTOMATION,
        published_from_thread_id="t-1",
    )
    assert t.space_type == SpaceType.WORKSPACE
    assert t.source == ThreadSource.AUTOMATION
    assert t.published_from_thread_id == "t-1"


def test_space_type_enum_values():
    assert SpaceType.PERSONAL.value == "personal"
    assert SpaceType.WORKSPACE.value == "workspace"


def test_thread_source_enum_values():
    assert ThreadSource.MANUAL.value == "manual"
    assert ThreadSource.AUTOMATION.value == "automation"
    assert ThreadSource.CHANNEL.value == "channel"


def test_thread_id_required():
    """Constructor enforces required positional fields by attribute presence."""
    t = Thread(id="t-3", title="x", user_id="u", workspace_id="w")
    assert t.id == "t-3"


def test_thread_round_trip_to_dict():
    t = Thread(
        id="t-4",
        title="hello",
        user_id="u-1",
        workspace_id="ws-1",
        space_type=SpaceType.WORKSPACE,
        source=ThreadSource.CHANNEL,
        published_from_thread_id="t-1",
    )
    d = {
        "id": t.id,
        "title": t.title,
        "user_id": t.user_id,
        "workspace_id": t.workspace_id,
        "space_type": t.space_type.value,
        "source": t.source.value,
        "published_from_thread_id": t.published_from_thread_id,
    }
    assert d["space_type"] == "workspace"
    assert d["source"] == "channel"
    assert d["published_from_thread_id"] == "t-1"
