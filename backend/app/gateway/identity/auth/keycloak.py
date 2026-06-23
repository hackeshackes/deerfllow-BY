"""Keycloak-specific OIDC provider.

Keycloak quirk: groups claim contains paths like '/engineering'.
We strip the leading slash and any parent path.
"""
from __future__ import annotations

from .oidc import GenericOIDCProvider
from .provider import OIDCUserInfo


class KeycloakProvider(GenericOIDCProvider):
    """Keycloak OIDC adapter with path-stripped group extraction."""

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        **kwargs,
    ):
        super().__init__(
            name="keycloak",
            issuer_url=issuer_url,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "keycloak"

    async def exchange_code(self, code: str, redirect_uri: str) -> OIDCUserInfo:
        info = await super().exchange_code(code, redirect_uri)
        stripped = [g.lstrip("/").split("/")[-1] for g in info.groups if g]
        return OIDCUserInfo(
            sub=info.sub,
            email=info.email,
            name=info.name,
            groups=stripped,
            raw_claims=info.raw_claims,
        )
