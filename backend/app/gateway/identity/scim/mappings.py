"""SCIM ↔ MicX internal user model conversion."""
from __future__ import annotations

from .models import SCIMUser


def scim_user_to_internal(scim: SCIMUser) -> dict:
    """Convert SCIM user to internal dict representation."""
    return {
        "id": scim.id,
        "email": scim.emails[0] if scim.emails else "",
        "name": scim.display_name or scim.userName,
        "active": scim.active,
        "groups": scim.groups,
    }


def internal_to_scim_user(internal: dict) -> SCIMUser:
    """Convert internal dict to SCIM user for outgoing requests."""
    return SCIMUser(
        id=internal.get("id", ""),
        userName=internal.get("email", internal.get("userName", "")),
        emails=[internal["email"]] if internal.get("email") else [],
        display_name=internal.get("name", ""),
        active=internal.get("active", True),
        groups=internal.get("groups", []),
    )