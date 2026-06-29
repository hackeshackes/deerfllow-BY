"""Thread domain model — v1.5.5 with space/source extensions.

A thread lives in exactly one space and originates from exactly one source.
`space_type` partitions threads by visibility scope (personal vs workspace);
`source` partitions by how the thread was created (manual user action,
scheduled automation result, or inbound from an external channel).
`published_from_thread_id` is non-null only for workspace-scope threads
that were promoted from a personal thread — it preserves the lineage so
downstream consumers can show "originally posted in /u/me".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SpaceType(str, Enum):
    PERSONAL = "personal"
    WORKSPACE = "workspace"


class ThreadSource(str, Enum):
    MANUAL = "manual"          # User-created via the chat UI
    AUTOMATION = "automation"  # Result of a scheduled task
    CHANNEL = "channel"        # Inbound from external channel (Feishu/DingTalk/...)


@dataclass
class Thread:
    id: str
    title: str
    user_id: str
    workspace_id: str
    space_type: SpaceType = SpaceType.PERSONAL
    source: ThreadSource = ThreadSource.MANUAL
    published_from_thread_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
