from deerflow.auth_context import (
    current_user_email,
    current_user_id,
    current_user_role,
    current_workspace_id,
    current_workspace_role,
)


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


__all__ = [
    "current_user_email",
    "current_user_id",
    "current_user_role",
    "current_workspace_id",
    "current_workspace_role",
    "get_current_user_email",
    "get_current_user_id",
    "get_current_user_role",
    "get_current_workspace_id",
    "get_current_workspace_role",
]
