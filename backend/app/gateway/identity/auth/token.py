"""JWT access token + refresh token management."""
from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from jose import JWTError, jwt


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    email: str
    workspace_id: str
    roles: list[str] = field(default_factory=list)
    expires_at: int = 0


class TokenError(Exception):
    """Token verification failed."""


def issue_access_token(payload: TokenPayload, secret: str) -> str:
    if not secret or len(secret) < 32:
        raise ValueError("secret must be ≥32 chars")
    return jwt.encode(
        {
            "sub": payload.sub,
            "email": payload.email,
            "workspace_id": payload.workspace_id,
            "roles": payload.roles,
            "exp": payload.expires_at,
            "iat": int(time.time()),
        },
        secret,
        algorithm="HS256",
    )


def verify_token(token: str, secret: str) -> TokenPayload:
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as e:
        msg = str(e).lower()
        if "expired" in msg:
            raise TokenError(f"token expired: {e}") from e
        raise TokenError(f"invalid token: {e}") from e
    return TokenPayload(
        sub=claims["sub"],
        email=claims["email"],
        workspace_id=claims["workspace_id"],
        roles=claims.get("roles", []),
        expires_at=claims["exp"],
    )


def generate_refresh_token() -> str:
    """Generate a cryptographically random refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    """Hash a refresh token for storage (never store plaintext)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()