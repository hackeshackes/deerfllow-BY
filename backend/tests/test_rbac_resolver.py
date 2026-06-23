import pytest
from app.gateway.identity.rbac.resolver import ResourceOwnershipResolver


def test_resolve_thread_owner_workspace():
    """ResourceOwnershipResolver should map resource → (workspace_id, owner_id)."""
    # Stub: in real impl, queries DB
    r = ResourceOwnershipResolver()
    ws, owner = r.resolve("thread", "thread-123")
    # Default stub returns ("default", "anonymous")
    assert ws == "default"
    assert owner == "anonymous"


def test_resolve_unknown_resource_returns_default():
    r = ResourceOwnershipResolver()
    ws, owner = r.resolve("unknown", "x")
    assert ws == "default"
    assert owner == "anonymous"
