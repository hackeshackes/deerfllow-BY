"""OIDC login/callback/logout endpoints.

GET  /auth/oidc/login?provider=X&redirect_uri=Y → 307 to IdP
GET  /auth/oidc/callback?provider=X&code=Y&state=Z → exchange, set session cookie, redirect
POST /auth/oidc/logout → clear session
"""
from __future__ import annotations

import secrets
from typing import Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..auth.provider import AuthError, OIDCProvider

router = APIRouter(prefix="/auth/oidc", tags=["auth-oidc"])

# In-process provider registry. Production: persist to DB.
_registry: Dict[str, OIDCProvider] = {}


def register_provider(provider: OIDCProvider) -> None:
    """Register an OIDC provider instance."""
    _registry[provider.name] = provider


def get_provider(name: str) -> OIDCProvider:
    if name not in _registry:
        raise HTTPException(status_code=404, detail=f"unknown OIDC provider: {name}")
    return _registry[name]


@router.get("/login")
async def login(
    provider: str = Query(...),
    redirect_uri: str = Query(...),
) -> RedirectResponse:
    p = get_provider(provider)
    state = secrets.token_urlsafe(32)
    # In production: persist state → redirect_uri in session for CSRF check
    url = await p.get_authorization_url(state, redirect_uri)
    return RedirectResponse(url, status_code=307)


@router.get("/callback")
async def callback(
    provider: str = Query(...),
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
) -> RedirectResponse:
    p = get_provider(provider)
    try:
        info = await p.exchange_code(code, redirect_uri)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    # In production: look up or create user, issue session cookie
    # Stub: just redirect to app
    return RedirectResponse(redirect_uri, status_code=307)


@router.post("/logout")
async def logout() -> dict:
    # In production: invalidate session
    return {"status": "ok"}
