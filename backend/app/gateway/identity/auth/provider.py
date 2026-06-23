"""Abstract OIDC provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OIDCUserInfo:
    """Standardized user info from any OIDC provider."""
    sub: str
    email: str
    name: str
    groups: list[str] = field(default_factory=list)
    raw_claims: dict = field(default_factory=dict)


class AuthError(Exception):
    """Authentication failed."""


class OIDCProvider(ABC):
    """Abstract OIDC provider. Concrete adapters implement name + endpoints."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'keycloak', 'okta'."""

    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Return IdP authorization URL to redirect user to."""

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OIDCUserInfo:
        """Exchange authorization code for user info. Raises AuthError on failure."""

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        """Default: not implemented. Subclasses may override."""
        raise NotImplementedError(f"{self.name} does not support refresh in this implementation")