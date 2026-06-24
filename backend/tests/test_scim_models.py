import pytest
from app.gateway.identity.scim.models import SCIMUser, SCIMGroup


def test_scim_user_roundtrip():
    u = SCIMUser(
        id="u-1",
        userName="alice",
        emails=["alice@x.com"],
        display_name="Alice",
        active=True,
        groups=["eng", "admins"],
    )
    d = u.to_dict()
    assert d["userName"] == "alice"
    assert d["active"] is True
    restored = SCIMUser.from_dict(d)
    assert restored.id == "u-1"
    assert restored.emails == ["alice@x.com"]


def test_scim_group_roundtrip():
    g = SCIMGroup(id="g-1", display_name="Engineering", members=["u-1", "u-2"])
    d = g.to_dict()
    assert d["displayName"] == "Engineering"
    restored = SCIMGroup.from_dict(d)
    assert restored.members == ["u-1", "u-2"]
