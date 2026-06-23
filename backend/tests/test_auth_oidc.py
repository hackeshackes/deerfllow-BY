import pytest
import respx
from httpx import Response

from app.gateway.identity.auth.oidc import GenericOIDCProvider
from app.gateway.identity.auth.provider import AuthError


@pytest.fixture
def provider():
    return GenericOIDCProvider(
        name="test-idp",
        issuer_url="https://idp.example.com",
        client_id="cid",
        client_secret="csec",
    )

@respx.mock
@pytest.mark.asyncio
async def test_get_authorization_url(provider):
    respx.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://idp.example.com/auth",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        })
    )
    url = await provider.get_authorization_url("state-xyz", "https://app/cb")
    assert url.startswith("https://idp.example.com/auth")
    assert "client_id=cid" in url
    assert "state=state-xyz" in url

@respx.mock
@pytest.mark.asyncio
async def test_exchange_code_success(provider):
    respx.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://idp.example.com/auth",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        })
    )
    respx.post("https://idp.example.com/token").mock(
        return_value=Response(200, json={"access_token": "at-123"})
    )
    respx.get("https://idp.example.com/userinfo").mock(
        return_value=Response(200, json={
            "sub": "u-1",
            "email": "u@ex.com",
            "name": "U",
            "groups": ["g1"],
        })
    )
    info = await provider.exchange_code("code-abc", "https://app/cb")
    assert info.sub == "u-1"
    assert info.email == "u@ex.com"
    assert info.groups == ["g1"]

@respx.mock
@pytest.mark.asyncio
async def test_exchange_code_failure_raises(provider):
    respx.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://idp.example.com/auth",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        })
    )
    respx.post("https://idp.example.com/token").mock(
        return_value=Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(AuthError, match="token exchange failed"):
        await provider.exchange_code("bad", "https://app/cb")
