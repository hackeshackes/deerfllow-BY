"""SAML IdP abstractions — vendor-agnostic."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAMLUserInfo:
    """User identity returned by a SAML IdP after a successful ACS callback."""

    name_id: str
    email: str
    name: str
    groups: list[str]
