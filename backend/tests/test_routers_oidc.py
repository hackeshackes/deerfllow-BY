import pytest
from fastapi.testclient import TestClient
from app.gateway.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_oidc_login_initiates_redirect(client, monkeypatch):
    """GET /auth/oidc/login?provider=keycloak should redirect to IdP."""
    from app.gateway.identity.auth import keycloak as kc_mod
    from app.gateway.identity.auth.provider import OIDCProvider, OIDCUserInfo
    from app.gateway.identity.routers import oidc as router

    class FakeKC(OIDCProvider):
        @property
        def name(self): return "keycloak"
        async def get_authorization_url(self, state, redirect_uri):
            return f"https://idp.test/auth?state={state}"
        async def exchange_code(self, code, redirect_uri):
            return OIDCUserInfo(sub="u", email="u@x.com", name="U")

    router.register_provider(FakeKC())
    resp = client.get("/auth/oidc/login?provider=keycloak&redirect_uri=https://app/cb", follow_redirects=False)
    assert resp.status_code == 307
    assert "idp.test" in resp.headers["location"]