import pytest
import respx
from httpx import Response
from app.gateway.identity.auth.authing import AuthingProvider


@pytest.fixture
def provider():
    return AuthingProvider(
        issuer_url="https://micx.authing.cn",
        client_id="6334",
        client_secret="sec",
    )


@respx.mock
@pytest.mark.asyncio
async def test_authing_provider(provider):
    respx.get("https://micx.authing.cn/.well-known/openid-configuration").mock(
        return_value=Response(200, json={
            "authorization_endpoint": "https://micx.authing.cn/oidc/auth",
            "token_endpoint": "https://micx.authing.cn/oidc/token",
            "userinfo_endpoint": "https://micx.authing.cn/oidc/userinfo",
        })
    )
    respx.post("https://micx.authing.cn/oidc/token").mock(
        return_value=Response(200, json={"access_token": "at"})
    )
    respx.get("https://micx.authing.cn/oidc/userinfo").mock(
        return_value=Response(200, json={
            "sub": "63xxx",
            "email": "dave@corp.cn",
            "name": "Dave",
            "groups": ["研发组"],
        })
    )
    info = await provider.exchange_code("c", "https://app/cb")
    assert info.email == "dave@corp.cn"
    assert info.groups == ["研发组"]