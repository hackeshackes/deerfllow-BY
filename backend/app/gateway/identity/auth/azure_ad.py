"""Azure AD (Microsoft Entra ID) OIDC provider."""
from __future__ import annotations

from .oidc import GenericOIDCProvider


class AzureADProvider(GenericOIDCProvider):
    """Azure AD / Entra ID OIDC adapter."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, **kwargs):
        issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        super().__init__(
            name="azure_ad",
            issuer_url=issuer,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "azure_ad"