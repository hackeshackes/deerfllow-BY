import pytest
from app.gateway.identity.rbac.models import (
    Role, RoleBinding, ResourceType, Action,
)


def test_role_creation():
    r = Role(id="r1", name="admin", scope="system", description="Full access")
    assert r.scope == "system"
    assert r.name == "admin"


def test_role_binding_requires_scope_id_for_dept():
    with pytest.raises(ValueError, match="scope_id required"):
        RoleBinding(
            id="rb1", user_id="u1", role_id="r1",
            scope="department", scope_id=None,
        )


def test_role_binding_system_scope_no_scope_id():
    rb = RoleBinding(id="rb1", user_id="u1", role_id="r1", scope="system", scope_id=None)
    assert rb.scope_id is None


def test_action_enum():
    assert Action.CREATE.value == "create"
    assert Action.READ.value == "read"


def test_resource_type_enum():
    assert ResourceType.WORKSPACE.value == "workspace"
    assert ResourceType.THREAD.value == "thread"
