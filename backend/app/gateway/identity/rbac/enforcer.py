"""Casbin enforcer wrapper for RBAC v2."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import casbin


class RBACEnforcer:
    """Thin wrapper around casbin.Enforcer with our model + policies."""

    def __init__(self, model_path: str | None = None, policy_path: str | None = None):
        if model_path is None:
            model_path = str(Path(__file__).parent / "model.conf")
        if policy_path is None:
            policy_path = str(Path(__file__).parent / "policies.csv")
        self._enforcer = casbin.Enforcer(model_path, policy_path)

    def check(
        self,
        user_id: str,
        roles: list[str],
        obj: str,
        act: str,
    ) -> bool:
        # Subject in casbin policy is a role; we pass each role as candidate
        # If any role allows, return True.
        # In a richer impl we'd resolve role_bindings for the user; here we
        # accept roles as input from upstream (middleware / decorator).
        for role in roles:
            if self._enforcer.enforce(role, obj, act):
                return True
        return False

    def add_policy(self, sub: str, obj: str, act: str) -> None:
        self._enforcer.add_policy(sub, obj, act)

    def remove_policy(self, sub: str, obj: str, act: str) -> None:
        self._enforcer.remove_policy(sub, obj, act)


@lru_cache(maxsize=1)
def get_enforcer() -> RBACEnforcer:
    return RBACEnforcer()
