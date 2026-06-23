"""Generic OIDC provider using authlib-style discovery.

Works with any standards-compliant OIDC IdP: Keycloak, Okta, Azure AD,
Google, Auth0, etc. For provider-specific quirks (e.g. group claim
location), wrap this in a subclass.
"""
from __future__ import annotations

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from .provider import AuthError, OIDCProvider, OIDCUserInfo


class GenericOIDCProvider(OIDCProvider):
    """Standards-compliant OIDC provider.

    Discovers endpoints via /.well-known/openid-configuration.
    """

    def __init__(
        self,
        name: str,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 10.0,
    ):
        self._name = name
        self._issuer = issuer_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._discovery: dict | None = None

    @property
    def name(self) -> str:
        return self._name

    async def _discover(self) -> dict:
        if self._discovery is None:
            url = f"{self._issuer}/.well-known/openid-configuration"
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                self._discovery = resp.json()
        return self._discovery

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        disc = await self._discover()
        client = AsyncOAuth2Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
            timeout=self._timeout,
        )
        url, _ = client.create_authorization_url(
            disc["authorization_endpoint"],
            state=state,
            redirect_uri=redirect_uri,
            scope="openid email profile groups",
        )
        return url

    async def exchange_code(self, code: str, redirect_uri: str) -> OIDCUserInfo:
        disc = await self._discover()
        async with AsyncOAuth2Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
            timeout=self._timeout,
        ) as client:
            try:
                await client.fetch_token(
                    disc["token_endpoint"],
                    code=code,
                    redirect_uri=redirect_uri,
                )
            except Exception as e:
                raise AuthError(f"token exchange failed: {e}") from e

            try:
                resp = await client.get(disc["userinfo_endpoint"])
                resp.raise_for_status()
                claims = resp.json()
            except Exception as e:
                raise AuthError(f"userinfo fetch failed: {e}") from e

        return OIDCUserInfo(
            sub=claims.get("sub", ""),
            email=claims.get("email", ""),
            name=claims.get("name", claims.get("preferred_username", "")),
            groups=claims.get("groups", []),
            raw_claims=claims,
        )
