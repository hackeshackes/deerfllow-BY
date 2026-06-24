"""SCIM 2.0 domain models (User, Group)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SCIMUser:
    id: str = ""
    userName: str = ""
    emails: list[str] = field(default_factory=list)
    display_name: str = ""
    active: bool = True
    groups: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "userName": self.userName,
            "emails": [{"value": e, "primary": True} for e in self.emails],
            "displayName": self.display_name,
            "active": self.active,
            "groups": [{"value": g} for g in self.groups],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SCIMUser":
        emails = [e.get("value", "") for e in d.get("emails", []) if isinstance(e, dict)]
        groups = [g.get("value", "") for g in d.get("groups", []) if isinstance(g, dict)]
        return cls(
            id=d.get("id", ""),
            userName=d.get("userName", ""),
            emails=emails,
            display_name=d.get("displayName", ""),
            active=d.get("active", True),
            groups=groups,
            raw=d,
        )


@dataclass
class SCIMGroup:
    id: str = ""
    display_name: str = ""
    members: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "members": [{"value": m} for m in self.members],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SCIMGroup":
        members = [m.get("value", "") for m in d.get("members", []) if isinstance(m, dict)]
        return cls(
            id=d.get("id", ""),
            display_name=d.get("displayName", ""),
            members=members,
            raw=d,
        )
