from __future__ import annotations

from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_user_role: ContextVar[str | None] = ContextVar("current_user_role", default=None)
current_user_email: ContextVar[str | None] = ContextVar("current_user_email", default=None)
current_workspace_id: ContextVar[str | None] = ContextVar("current_workspace_id", default=None)
current_workspace_role: ContextVar[str | None] = ContextVar("current_workspace_role", default=None)


def get_current_user_id() -> str | None:
    return current_user_id.get()


def get_current_user_role() -> str | None:
    return current_user_role.get()


def get_current_user_email() -> str | None:
    return current_user_email.get()


def get_current_workspace_id() -> str | None:
    return current_workspace_id.get()


def get_current_workspace_role() -> str | None:
    return current_workspace_role.get()
