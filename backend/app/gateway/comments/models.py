"""Comment domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CommentSource(str, Enum):
    USER = "user"        # Posted by a human via the UI
    AGENT = "agent"      # Posted by the AI agent as part of its response
    AUTOMATION = "automation"  # Posted by a scheduled task


@dataclass
class Comment:
    id: str
    thread_id: str
    author_id: str
    text: str
    source: CommentSource = CommentSource.USER
    # If this is a reply, the comment it replies to.
    parent_comment_id: str | None = None
    # User IDs mentioned in the text (parsed by the service layer).
    mentioned_user_ids: list[str] = field(default_factory=list)
    created_at: str = ""
