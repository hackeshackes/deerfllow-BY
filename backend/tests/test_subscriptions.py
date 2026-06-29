"""Tests for the subscriptions subsystem (Task 16 + 17 merged)."""
from __future__ import annotations

import pytest

from app.gateway.subscriptions.models import (
    NotifyChannel,
    Subscription,
    SubscriptionTarget,
    TargetKind,
)
from app.gateway.subscriptions.notifier import InMemoryNotifier
from app.gateway.subscriptions.service import (
    InMemorySubscriptionStore,
    SubscriptionService,
)


# ----------------------------------------------------------------- models
def test_subscription_creation():
    s = Subscription(
        id="sub-1",
        user_id="u-1",
        target=SubscriptionTarget(kind="thread", id="t-1"),
        notify_via=[NotifyChannel.INAPP],
    )
    assert s.target.kind == "thread"
    assert NotifyChannel.INAPP in s.notify_via


def test_subscription_target_validates_kind():
    with pytest.raises(ValueError, match="unknown target kind"):
        SubscriptionTarget(kind="widget", id="x")


def test_subscription_target_requires_id():
    with pytest.raises(ValueError, match="id must be non-empty"):
        SubscriptionTarget(kind="user", id="")


def test_target_kind_enum_values():
    assert TargetKind.THREAD.value == "thread"
    assert TargetKind.KNOWLEDGE.value == "knowledge"
    assert TargetKind.AUTOMATION.value == "automation"


def test_notify_channel_enum_values():
    assert NotifyChannel.INAPP.value == "inapp"
    assert NotifyChannel.EMAIL.value == "email"
    assert NotifyChannel.FEISHU.value == "feishu"
    assert NotifyChannel.DINGTALK.value == "dingtalk"


# ----------------------------------------------------------------- service
@pytest.fixture
def store():
    return InMemorySubscriptionStore()


@pytest.fixture
def notifier():
    return InMemoryNotifier()


@pytest.mark.asyncio
async def test_mention_triggers_notification_for_subscribed_user(store, notifier):
    await store.add(
        Subscription(
            id="s1",
            user_id="u-target",
            target=SubscriptionTarget(kind="user", id="u-target"),
            notify_via=[NotifyChannel.INAPP],
        )
    )
    svc = SubscriptionService(store=store, notifier=notifier)
    n = await svc.handle_mention(
        thread_id="t-1",
        mentioned_user_ids=["u-target"],
        actor_id="u-actor",
        text="hi @u-target",
    )
    assert n == 1
    assert notifier.sent[0].recipient == "u-target"
    assert "u-actor" in notifier.sent[0].text


@pytest.mark.asyncio
async def test_mention_unknown_user_is_noop(store, notifier):
    svc = SubscriptionService(store=store, notifier=notifier)
    n = await svc.handle_mention(
        thread_id="t-1",
        mentioned_user_ids=["u-nobody"],
        actor_id="u-actor",
        text="x",
    )
    assert n == 0
    assert notifier.sent == []


@pytest.mark.asyncio
async def test_mention_fans_out_to_multiple_users(store, notifier):
    for uid in ("u-a", "u-b", "u-c"):
        await store.add(
            Subscription(
                id=f"s-{uid}",
                user_id=uid,
                target=SubscriptionTarget(kind="user", id=uid),
                notify_via=[NotifyChannel.INAPP],
            )
        )
    svc = SubscriptionService(store=store, notifier=notifier)
    n = await svc.handle_mention(
        thread_id="t-1",
        mentioned_user_ids=["u-a", "u-b", "u-none"],
        actor_id="u-actor",
        text="hi all",
    )
    assert n == 2
    recipients = {nm.recipient for nm in notifier.sent}
    assert recipients == {"u-a", "u-b"}


@pytest.mark.asyncio
async def test_mention_text_truncated_to_100(store, notifier):
    await store.add(
        Subscription(
            id="s1",
            user_id="u-t",
            target=SubscriptionTarget(kind="user", id="u-t"),
            notify_via=[NotifyChannel.INAPP],
        )
    )
    svc = SubscriptionService(store=store, notifier=notifier)
    long_text = "x" * 500
    await svc.handle_mention(
        thread_id="t-1",
        mentioned_user_ids=["u-t"],
        actor_id="u-actor",
        text=long_text,
    )
    # The notification prefix + 100 'x' chars
    assert len(notifier.sent[0].text) <= 100 + len("u-actor mentioned you: ")


@pytest.mark.asyncio
async def test_store_remove_returns_count(store):
    await store.add(
        Subscription(
            id="s1",
            user_id="u",
            target=SubscriptionTarget(kind="thread", id="t-1"),
            notify_via=[NotifyChannel.INAPP],
        )
    )
    await store.add(
        Subscription(
            id="s2",
            user_id="u2",
            target=SubscriptionTarget(kind="thread", id="t-1"),
            notify_via=[NotifyChannel.EMAIL],
        )
    )
    n = await store.remove(SubscriptionTarget(kind="thread", id="t-1"))
    assert n == 2
    assert await store.get_for_target(SubscriptionTarget(kind="thread", id="t-1")) == []
