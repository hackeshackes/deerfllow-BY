import pytest
import respx
from httpx import Response
from app.gateway.identity.auth.okta import OktaProvider


@pytest.fixture
def provider():
    return OktaProvider(
        issuer_url="https://corp.okta.com",
        client_id="0oa123",
        client_secret="sec",
    )


@respx.mock
@pytest.mark.asyncio
async def test_okta_groups_provider(provider):
    respx.get("https://corp.okta.com/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://corp.okta.com/oauth2/v1/authorize",
            "token_endpoint": "https://corp.okta.com/oauth2/v1/token",
            "userinfo_endpoint": "https://corp.okta.com/oauth2/v1/userinfo",
        })
    )
    respx.post("https://corp.okta.com/oauth2/v1/token").mock(
        return_value=Response(200, json={"access_token": "at"})
    )
    respx.get("https://corp.okta.com/oauth2/v1/userinfo").mock(
        return_value=Response(200, json={
            "sub": "00u123",
            "email": "bob@corp.io",
            "name": "Bob",
            "groups": ["Everyone", "Engineering"],
        })
    )
    info = await provider.exchange_code("c", "https://app/cb")
    assert info.groups == ["Everyone", "Engineering"]