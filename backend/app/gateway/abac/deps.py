"""Reusable ABAC gating dependency (v1.7 M2.4).

Exposes a FastAPI dependency factory used by *any* router that wants to gate
an action through ABAC instead of an inline ``role == "owner"`` check::

    from app.gateway.abac.deps import require_abac

    @router.delete("/threads/{id}")
    async def delete_thread(
        user: AuthUser = Depends(require_abac("delete", "thread", workspace_id)),
        ...
    )

The dependency:

* builds an ABAC :class:`Subject` from the authenticated user plus its
  workspace memberships (mirroring the collab publish router);
* builds a :class:`Resource` from the caller-supplied ``resource_type`` and
  ``workspace_id``;
* evaluates the configured policy set (custom file, or the built-in
  ``owner-only`` / ``workspace-member`` presets) via :func:`evaluate`;
* raises 403 on a deny / no-match (fail-closed).

Backward compatibility: with no policies file configured, the gate uses the
built-in presets — behaviourally identical to v1.6.1 RBAC gating, so existing
owner-gated routes keep working as the operator introduces ABAC policy files.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException

from app.gateway.auth import AuthUser, list_workspaces_for_user, require_user

from .evaluator import Action, Resource, Subject, evaluate
from .policies_file import PoliciesCache, resolve_policies

# Configured in one place so the operator can point the gate at a policies file.
_CONFIGURED_POLICY_PATH: str | None = None
_POLICIES_CACHE: PoliciesCache | None = None


def configure_abac_policies_path(path: str | None) -> None:
    """Point the ABAC gate at an operator policies file (or None to use presets).

    Reconfiguring also resets the cache so the next gate call reads fresh.
    """
    global _CONFIGURED_POLICY_PATH, _POLICIES_CACHE
    _CONFIGURED_POLICY_PATH = path
    if path is None:
        _POLICIES_CACHE = None
    else:
        _POLICIES_CACHE = PoliciesCache(path)


def _policy_set() -> list[Any]:
    """Return the active policy set (cached from the configured path or built-in)."""
    if _POLICIES_CACHE is not None:
        return _POLICIES_CACHE.get()
    return resolve_policies(_CONFIGURED_POLICY_PATH)


def _subject_from(user: AuthUser) -> Subject:
    memberships = list_workspaces_for_user(user.id)
    return Subject(
        id=user.id,
        role=user.role,
        attrs={"workspaces": [m.workspace_id for m in memberships]},
    )


def require_abac(
    verb: str,
    resource_type: str,
    workspace_id: str = "",
) -> Callable[..., Awaitable[AuthUser]]:
    """Return a FastAPI dependency that authorizes ``verb`` on a resource.

    The returned dependency returns the authenticated user when allowed, or
    raises ``HTTPException(403)`` when denied / no policy matches.
    """

    async def _gate(user: AuthUser = Depends(require_user)) -> AuthUser:
        subject = _subject_from(user)
        resource = Resource(
            type=resource_type,
            id="",
            attrs={"workspace_id": workspace_id} if workspace_id else {},
        )
        decision = evaluate(
            subject=subject,
            resource=resource,
            action=Action(verb=verb),
            policies=_policy_set(),
        )
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)
        return user

    return _gate


__all__ = [
    "configure_abac_policies_path",
    "require_abac",
]