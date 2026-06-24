"""FastAPI permission decorator for RBAC v2."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import HTTPException

from .enforcer import get_enforcer


def require_permission(obj: str, act: str) -> Callable:
    """Decorator: require the caller's roles to permit (obj, act).

    The decorated function must accept a `user_roles: list[str]` parameter
    (typically via FastAPI Depends).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, user_roles: list[str], **kwargs):
            enforcer = get_enforcer()
            # Use a placeholder user_id; subject is role, so enforcer checks role only
            if not enforcer.check("u", user_roles, obj, act):
                raise HTTPException(
                    status_code=403,
                    detail=f"permission denied: {obj}/{act}",
                )
            return func(*args, user_roles=user_roles, **kwargs)
        return wrapper
    return decorator
