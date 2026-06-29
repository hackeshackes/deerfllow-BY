"""Subscription service: @mention fan-out + delivery.

The service knows nothing about the store or notifier's concrete types —
callers inject them. This keeps the service trivially testable and lets the
production wiring swap in a Postgres-backed store without changing the
service.
"""
from __future__ import annotations

from .models import Subscription, SubscriptionTarget
from .notifier import Notification


class SubscriptionStore:
    """Abstract store — production: Postgres; tests: in-memory."""

    async def get_for_target(self, target: SubscriptionTarget) -> list[Subscription]: ...

    async def add(self, sub: Subscription) -> None: ...

    async def remove(self, target: SubscriptionTarget) -> int:
        """Remove all subscriptions for the target. Returns the count removed."""
        return 0


class InMemorySubscriptionStore(SubscriptionStore):
    def __init__(self) -> None:
        self._items: list[Subscription] = []

    async def get_for_target(self, target: SubscriptionTarget) -> list[Subscription]:
        return [s for s in self._items if s.target == target]

    async def add(self, sub: Subscription) -> None:
        self._items.append(sub)

    async def remove(self, target: SubscriptionTarget) -> int:
        before = len(self._items)
        self._items = [s for s in self._items if s.target != target]
        return before - len(self._items)


class SubscriptionService:
    def __init__(self, store: SubscriptionStore, notifier) -> None:
        self._store = store
        self._notifier = notifier

    async def handle_mention(
        self,
        thread_id: str,
        mentioned_user_ids: list[str],
        actor_id: str,
        text: str,
    ) -> int:
        """Send a notification for each mentioned user who has a subscription.

        Returns the number of notifications sent. Users who are mentioned but
        have no subscription are silently skipped — they will receive no
        notification until they explicitly opt in.
        """
        sent = 0
        for uid in mentioned_user_ids:
            target = SubscriptionTarget(kind="user", id=uid)
            subs = await self._store.get_for_target(target)
            for sub in subs:
                await self._notifier.send(
                    Notification(
                        recipient=uid,
                        text=f"{actor_id} mentioned you: {text[:100]}",
                        metadata={
                            "thread_id": thread_id,
                            "actor_id": actor_id,
                            "channels": [c.value for c in sub.notify_via],
                        },
                    )
                )
                sent += 1
        return sent
