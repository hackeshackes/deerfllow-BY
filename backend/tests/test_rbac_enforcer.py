import pytest
from app.gateway.identity.rbac.enforcer import RBACEnforcer, get_enforcer


def test_admin_can_do_anything():
    e = RBACEnforcer()
    assert e.check("u1", ["role:admin"], "thread/abc", "create") is True
    assert e.check("u1", ["role:admin"], "config/foo", "delete") is True


def test_member_can_create_thread():
    e = RBACEnforcer()
    assert e.check("u1", ["role:member"], "thread/abc", "create") is True
    assert e.check("u1", ["role:member"], "thread/abc", "delete") is False


def test_guest_cannot_read_workspace():
    e = RBACEnforcer()
    assert e.check("u1", ["role:guest"], "workspace/abc", "read") is False


def test_no_roles_denies():
    e = RBACEnforcer()
    assert e.check("u1", [], "thread/abc", "read") is False


def test_get_enforcer_returns_singleton():
    e1 = get_enforcer()
    e2 = get_enforcer()
    assert e1 is e2


def test_glob_pattern_matches_subpath():
    e = RBACEnforcer()
    # role:member policy is "thread/*" with action "read"
    assert e.check("u1", ["role:member"], "thread/abc/sub", "read") is True
