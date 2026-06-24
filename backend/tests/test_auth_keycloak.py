import pytest
import respx
from httpx import Response
from app.gateway.identity.auth.keycloak import KeycloakProvider


@pytest.fixture
def provider():
    return KeycloakProvider(
        issuer_url="https://kc.example.com/realms/micx",
        client_id="micx-web",
        client_secret="sec-123",
    )


@respx.mock
@pytest.mark.asyncio
async def test_keycloak_extracts_realm_groups(provider):
    respx.get("https://kc.example.com/realms/micx/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://kc.example.com/realms/micx/protocol/openid-connect/auth",
            "token_endpoint": "https://kc.example.com/realms/micx/protocol/openid-connect/token",
            "userinfo_endpoint": "https://kc.example.com/realms/micx/protocol/openid-connect/userinfo",
        })
    )
    respx.post("https://kc.example.com/realms/micx/protocol/openid-connect/token").mock(
        return_value=Response(200, json={"access_token": "at"})
    )
    respx.get("https://kc.example.com/realms/micx/protocol/openid-connect/userinfo").mock(
        return_value=Response(200, json={
            "sub": "kc-user-1",
            "email": "alice@corp.io",
            "name": "Alice",
            "groups": ["/engineering", "/admins"],  # Keycloak path-prefixed
        })
    )
    info = await provider.exchange_code("c", "https://app/cb")
    # Keycloak-specific: strip leading slash
    assert info.groups == ["engineering", "admins"]
