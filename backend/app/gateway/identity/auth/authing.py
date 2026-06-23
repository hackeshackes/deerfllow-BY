"""Authing (China) OIDC provider."""
from __future__ import annotations

from .oidc import GenericOIDCProvider


class AuthingProvider(GenericOIDCProvider):
    """Authing OIDC adapter — name passthrough, no group transformation."""

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        **kwargs,
    ):
        super().__init__(
            name="authing",
            issuer_url=issuer_url,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "authing"