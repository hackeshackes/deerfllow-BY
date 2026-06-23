import pytest
import respx
from httpx import Response
from app.gateway.identity.auth.azure_ad import AzureADProvider


@pytest.fixture
def provider():
    return AzureADProvider(
        tenant_id="common",
        client_id="app-id",
        client_secret="sec",
    )


@respx.mock
@pytest.mark.asyncio
async def test_azure_ad_groups_provider(provider):
    respx.get("https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
        })
    )
    respx.post("https://login.microsoftonline.com/common/oauth2/v2.0/token").mock(
        return_value=Response(200, json={"access_token": "at"})
    )
    respx.get("https://graph.microsoft.com/oidc/userinfo").mock(
        return_value=Response(200, json={
            "sub": "abc",
            "email": "carol@corp.io",
            "name": "Carol",
            "groups": ["dept-eng"],
        })
    )
    info = await provider.exchange_code("c", "https://app/cb")
    assert info.groups == ["dept-eng"]


def test_azure_ad_issuer_uses_tenant():
    p = AzureADProvider(tenant_id="my-tenant", client_id="x", client_secret="y")
    assert "my-tenant" in p._issuer