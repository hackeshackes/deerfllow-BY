import pytest
from app.gateway.identity.scim.mappings import scim_user_to_internal, internal_to_scim_user
from app.gateway.identity.scim.models import SCIMUser


def test_scim_to_internal():
    scim = SCIMUser(
        id="scim-1",
        userName="alice",
        emails=["alice@corp.io"],
        display_name="Alice",
        active=True,
        groups=["eng"],
    )
    internal = scim_user_to_internal(scim)
    assert internal["id"] == "scim-1"
    assert internal["email"] == "alice@corp.io"
    assert internal["name"] == "Alice"
    assert internal["active"] is True
    assert internal["groups"] == ["eng"]


def test_internal_to_scim():
    internal = {
        "id": "scim-1",
        "email": "bob@x",
        "name": "Bob",
        "active": False,
        "groups": ["g1"],
    }
    scim = internal_to_scim_user(internal)
    assert scim.userName == "bob@x"
    assert scim.active is False
    assert scim.groups == ["g1"]