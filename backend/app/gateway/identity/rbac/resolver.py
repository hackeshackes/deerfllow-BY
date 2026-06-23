"""Resource ownership resolver.

Maps (resource_type, resource_id) → (workspace_id, owner_user_id).
Used by the RBAC middleware to compute effective permissions.

In this version, the resolver returns defaults; subsequent tasks will
add real DB-backed lookups for each resource type.
"""
from __future__ import annotations


class ResourceOwnershipResolver:
    """Stub resolver. Replace with DB-backed impl in subsequent tasks."""

    def resolve(self, resource_type: str, resource_id: str) -> tuple[str, str]:
        # STUB: replace with DB queries per resource_type in v1.5.5+ follow-up
        return ("default", "anonymous")
