"""Smoke test: ensure all identity modules can be imported."""
def test_identity_subsystem_imports():
    from app.gateway.identity import config, crypto
    from app.gateway.identity.auth import token  # noqa
    from app.gateway.identity.rbac import enforcer  # noqa
    from app.gateway.identity.audit import writer  # noqa
    from app.gateway.identity.scim import mappings  # noqa

def test_config_and_crypto_compose():
    from app.gateway.identity.config import get_identity_config
    from app.gateway.identity.crypto import encrypt_secret, decrypt_secret
    cfg = get_identity_config()
    assert cfg is not None
    enc = encrypt_secret("smoke-test")
    assert decrypt_secret(enc) == "smoke-test"