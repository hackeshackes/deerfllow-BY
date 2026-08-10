"""ABAC owner-gating for the connectors router (v1.7 M2 C).

The list / dlq-list / dlq-delete endpoints previously had NO authentication
(any caller, authed or not, reached them). Now they are owner-gated via
``require_abac``: unauthenticated → 401, member → 403, owner → 200. The inbound
webhook keeps its platform-secret check (it is called by external IM systems,
not by a user session) and is intentionally NOT user-authenticated.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth import AuthUser, require_user
from app.gateway.connectors.routers.connectors import router


def _user(role: str) -> AuthUser:
    return AuthUser(
        id="u1",
        email="u@x.com",
        role=role,
        name="U",
        status="active",
        password_hash="x",
        salt="y",
    )


def _app(role: str | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if role is not None:
        app.dependency_overrides[require_user] = lambda: _user(role)
    return app


def test_list_connectors_unauthenticated_401(monkeypatch):
    # In pytest the session resolver seeds an owner, so simulate a truly
    # unauthenticated request by making require_user fail.
    monkeypatch.setattr(
        "app.gateway.auth.session_user_from_request", lambda _req: None
    )
    with TestClient(_app(None)) as client:
        assert client.get("/api/connectors").status_code == 401


def test_list_connectors_member_403():
    with TestClient(_app("member")) as client:
        assert client.get("/api/connectors").status_code == 403


def test_list_connectors_owner_200():
    with TestClient(_app("owner")) as client:
        assert client.get("/api/connectors").status_code == 200


def test_dlq_list_owner_200():
    with TestClient(_app("owner")) as client:
        assert client.get("/api/connectors/dlq").status_code == 200


def test_dlq_list_member_403():
    with TestClient(_app("member")) as client:
        assert client.get("/api/connectors/dlq").status_code == 403


def test_dlq_delete_owner_204():
    with TestClient(_app("owner")) as client:
        # A missing id → 404 (owner reached the handler), not a 401/403.
        assert client.delete("/api/connectors/dlq/missing").status_code == 404


def test_dlq_delete_member_403():
    with TestClient(_app("member")) as client:
        assert client.delete("/api/connectors/dlq/missing").status_code == 403


def test_webhook_still_uses_secret_check_unauthenticated():
    """Webhook (external platform → our server) is NOT user-gated; bad secret
    still yields 403/404, proving ABAC was not bolted onto the inbound path."""
    with TestClient(_app(None)) as client:
        resp = client.post(
            "/api/connectors/feishu/webhook",
            params={"secret": "invalid"},
            json={"text": "hi"},
        )
        assert resp.status_code in (403, 404)