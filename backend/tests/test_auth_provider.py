import pytest
from app.gateway.identity.auth.provider import OIDCProvider, OIDCUserInfo, AuthError

class FakeProvider(OIDCProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        from urllib.parse import quote
        return f"https://fake-idp/auth?state={state}&redirect_uri={quote(redirect_uri, safe='')}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OIDCUserInfo:
        return OIDCUserInfo(
            sub="user-123",
            email="user@example.com",
            name="Test User",
            groups=["engineering"],
        )

def test_provider_abstract():
    with pytest.raises(TypeError):
        OIDCProvider()  # type: ignore

def test_fake_provider_returns_url():
    import asyncio
    p = FakeProvider()
    url = asyncio.run(p.get_authorization_url("xyz", "https://app/cb"))
    assert "state=xyz" in url
    assert "redirect_uri=https%3A%2F%2Fapp%2Fcb" in url

def test_fake_provider_exchange():
    import asyncio
    p = FakeProvider()
    info = asyncio.run(p.exchange_code("abc", "https://app/cb"))
    assert info.sub == "user-123"
    assert "engineering" in info.groups