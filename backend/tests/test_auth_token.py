import time
import pytest
from jose import jwt as jose_jwt
from app.gateway.identity.auth.token import (
    issue_access_token, verify_token, TokenError,
    TokenPayload, hash_refresh_token, generate_refresh_token,
)

SECRET = "test-secret-must-be-long-enough-32+chars-12345"

def test_issue_and_verify_roundtrip():
    payload = TokenPayload(
        sub="user-1",
        email="u@x.com",
        workspace_id="ws-1",
        roles=["admin"],
        expires_at=int(time.time()) + 3600,
    )
    token = issue_access_token(payload, secret=SECRET)
    decoded = verify_token(token, secret=SECRET)
    assert decoded.sub == "user-1"
    assert decoded.roles == ["admin"]

def test_expired_token_raises():
    payload = TokenPayload(
        sub="user-1", email="u@x.com", workspace_id="ws-1",
        roles=[], expires_at=int(time.time()) - 10,
    )
    token = issue_access_token(payload, secret=SECRET)
    with pytest.raises(TokenError, match="expired"):
        verify_token(token, secret=SECRET)

def test_wrong_secret_raises():
    payload = TokenPayload(
        sub="user-1", email="u@x.com", workspace_id="ws-1",
        roles=[], expires_at=int(time.time()) + 3600,
    )
    token = issue_access_token(payload, secret=SECRET)
    with pytest.raises(TokenError, match="invalid"):
        verify_token(token, secret="different-secret-also-32+chars-long-99999")

def test_refresh_token_randomness():
    t1 = generate_refresh_token()
    t2 = generate_refresh_token()
    assert t1 != t2
    assert len(t1) >= 32

def test_refresh_token_hash_is_deterministic():
    raw = "rt-abc"
    h1 = hash_refresh_token(raw)
    h2 = hash_refresh_token(raw)
    assert h1 == h2
    assert h1 != raw  # hash, not plaintext
