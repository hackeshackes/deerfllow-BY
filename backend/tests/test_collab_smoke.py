"""End-to-end smoke for the collaboration backend (Task 20).

Composes: Thread (with space/source) + SubscriptionService + InMemoryNotifier.
Verifies the wiring holds together — that a @mention on a workspace thread
can fan out to a subscriber's notifier.
"""
from __future__ import annotations

import pytest

from app.gateway.subscriptions.models import (
    NotifyChannel,
    Subscription,
    SubscriptionTarget,
)
from app.gateway.subscriptions.notifier import InMemoryNotifier
from app.gateway.subscriptions.service import (
    InMemorySubscriptionStore,
    SubscriptionService,
)
from app.gateway.threads.models import SpaceType, Thread, ThreadSource


def test_thread_with_space_and_source_roundtrip():
    t = Thread(
        id="t-1",
        title="Weekly recap",
        user_id="u-1",
        workspace_id="ws-1",
        space_type=SpaceType.WORKSPACE,
        source=ThreadSource.AUTOMATION,
    )
    assert t.space_type == SpaceType.WORKSPACE
    assert t.source == ThreadSource.AUTOMATION

    payload = {
        "id": t.id,
        "title": t.title,
        "space_type": t.space_type.value,
        "source": t.source.value,
        "published_from_thread_id": t.published_from_thread_id,
    }
    assert payload["space_type"] == "workspace"
    assert payload["source"] == "automation"


@pytest.mark.asyncio
async def test_mention_fanout_end_to_end():
    store = InMemorySubscriptionStore()
    notifier = InMemoryNotifier()
    await store.add(
        Subscription(
            id="s-bob",
            user_id="u-bob",
            target=SubscriptionTarget(kind="user", id="u-bob"),
            notify_via=[NotifyChannel.INAPP, NotifyChannel.EMAIL],
        )
    )
    svc = SubscriptionService(store=store, notifier=notifier)
    n = await svc.handle_mention(
        thread_id="t-1",
        mentioned_user_ids=["u-bob", "u-noone"],
        actor_id="u-alice",
        text="@bob see this thread",
    )
    assert n == 1
    assert notifier.sent[0].recipient == "u-bob"
    assert notifier.sent[0].metadata["thread_id"] == "t-1"
    assert "inapp" in notifier.sent[0].metadata["channels"]
    assert "email" in notifier.sent[0].metadata["channels"]


@pytest.mark.asyncio
async def test_publication_link_preserved_across_thread_lifecycle():
    """A workspace thread published from a personal thread keeps the lineage."""
    personal = Thread(
        id="t-1", title="draft", user_id="u-1", workspace_id="ws-1"
    )
    published = Thread(
        id="t-2",
        title="draft (published)",
        user_id="u-1",
        workspace_id="ws-1",
        space_type=SpaceType.WORKSPACE,
        source=ThreadSource.MANUAL,
        published_from_thread_id=personal.id,
    )
    assert published.published_from_thread_id == personal.id
    assert published.space_type == SpaceType.WORKSPACE
    assert personal.space_type == SpaceType.PERSONAL
