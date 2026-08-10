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
from app.gateway.connectors.base import BaseConnector, ConnectorMessage, ConnectorResponse
from app.gateway.connectors.routers.connectors import (
    _bridge,
    _dlq,
    router,
)


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


# --------------------------------------------------------------------------- #
# Full permission matrix (v1.7 M2 C hostile matrix test).
#
# Enumerates every route x identity cell and asserts the exact status code.
# Three management routes are user-authenticated + ABAC-gated; the inbound
# webhook is deliberately NOT user-gated (it is called by external IM systems)
# and is instead secret-checked. Unknown roles MUST fail closed (never allow).
# --------------------------------------------------------------------------- #


class _FakeConn(BaseConnector):
    name = "wbfake"
    display_name = "WB Fake"

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        return ConnectorResponse(success=True)

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        return [
            ConnectorMessage(
                text=payload.get("text", ""),
                target={"chat_id": payload.get("chat_id")},
            )
        ]


REGISTERED_NAME = "wbfake"
GOOD_SECRET = "good-secret"
BAD_SECRET = "bad-secret"


def _register_webhook_route() -> None:
    """Register a webhook route on the module-level singleton bridge.
    The mgmt routes' dlq store singleton is also reset for isolation."""
    _bridge.register(connector=_FakeConn(), secret=GOOD_SECRET)
    # keep the singleton dlq store pristine for the matrix runs
    _dlq.clear_all()


def _identities() -> list[tuple[str, str | None, int]]:
    """(label, role, expected_status). None role = unauthenticated (no cookie)."""
    return [
        ("unauthenticated", None, 401),
        ("member", "member", 403),
        ("owner", "owner", 200),
        # Unknown role must FAIL CLOSED, not accidentally allow.
        ("unknown-collaborator", "collaborator", 403),
        ("unknown-superadmin", "superadmin", 403),
    ]


def _matrix_app(role: str | None, monkeypatch) -> FastAPI:
    """Build an app whose session resolves to *role*.

    Unauthenticated (role None) is simulated the same way as the existing
    unauthenticated test: under pytest, ``session_user_from_request`` would
    otherwise short-circuit to the seeded owner, masking the real 401 path.
    """
    app = FastAPI()
    app.include_router(router)
    if role is None:
        monkeypatch.setattr(
            "app.gateway.auth.session_user_from_request", lambda _req: None
        )
    else:
        app.dependency_overrides[require_user] = lambda: _user(role)
    return app


def test_matrix_management_routes_full_identity_cross(monkeypatch):
    """Matrix every management route x every identity.

    Management routes are owner-gated:
      - unauthenticated             -> 401 (require_user)
      - member                      -> 403 (ABAC deny)
      - owner                       -> 200 (GET) / 204 (DELETE)
      - unknown role                -> 403 (ABAC fail-closed)

    For DELETE we seed a live dlq entry so the owner path yields a clean 204,
    and non-owners must NOT reach the handler (401/403 regardless of the id).
    """
    _dlq.clear_all()
    existing_id = _dlq.push({"source": "test", "error": "boom"})
    existing_id2 = _dlq.push({"source": "test2", "error": "boom2"})
    try:
        management_cases = [
            ("GET", "/api/connectors", None, 200),
            ("GET", "/api/connectors/dlq", None, 200),
            # owner deletes a real entry -> 204; member/unknown denied even though the
            # entry exists; unauthenticated -> 401.
            ("DELETE", "/api/connectors/dlq/{id}", existing_id, 204),
        ]
        for method, path_tmpl, path_id, ok_status in management_cases:
            for label, role, expected in _identities():
                path = (
                    path_tmpl.format(id=existing_id)
                    if path_id is not None
                    else path_tmpl
                )
                with TestClient(_matrix_app(role, monkeypatch)) as client:
                    resp = client.request(method, path)
                    expected_status = (
                        expected if (expected or 0) != 200 else ok_status
                    )
                    assert resp.status_code == expected_status, (
                        f"{label} on {method} {path}: expected {expected_status}, "
                        f"got {resp.status_code} body={resp.text[:120]!r}"
                    )
        # owner GET/dlq-list also returns 200 (asserted above via ok_status)
        # owner DELETE consumed existing_id; ensure it really removed it.
        with TestClient(_matrix_app("owner", monkeypatch)) as client:
            remaining = client.request("GET", "/api/connectors/dlq").json()["items"]
            assert remaining == [_dlq.get(existing_id2)], (
                f"owner delete did not remove the entry: {remaining!r}"
            )
    finally:
        _dlq.clear_all()


def test_matrix_DELETE_dlq_owner_reaches_handler_404():
    """Owner DELETE on a missing dlq id hits the handler => 404 (not 401/403)."""
    with TestClient(_app("owner")) as client:
        assert client.delete("/api/connectors/dlq/nope").status_code == 404


def test_webhook_not_user_authenticated_no_401(monkeypatch):
    """Webhook route has no user-auth dependency: even with NO session and an
    unknown role there is no 401. It is gated only by the shared secret."""
    for role in (None, "member", "owner", "collaborator", "superadmin"):
        with TestClient(_matrix_app(role, monkeypatch)) as client:
            resp = client.post(
                f"/api/connectors/{REGISTERED_NAME}/webhook",
                params={"secret": BAD_SECRET},
                json={"text": "hi"},
            )
            assert resp.status_code in (
                403,
                404,
            ), f"role={role} bad secret: expected 403/404, got {resp.status_code}"


def test_webhook_good_secret_owner_200(monkeypatch):
    """Owner (or any identity) with the correct secret dispatches 200."""
    _register_webhook_route()
    try:
        for role in (None, "owner", "member", "collaborator"):
            with TestClient(_matrix_app(role, monkeypatch)) as client:
                resp = client.post(
                    f"/api/connectors/{REGISTERED_NAME}/webhook",
                    params={"secret": GOOD_SECRET},
                    json={"text": "hello", "chat_id": "c1"},
                )
                assert resp.status_code == 200, (
                    f"webhook role={role} good secret: expected 200, "
                    f"got {resp.status_code} body={resp.text[:120]!r}"
                )
                payload = resp.json()
                assert payload["messages"][0]["text"] == "hello"
    finally:
        _bridge.unregister(REGISTERED_NAME)


def test_webhook_unknown_connector_404_with_any_identity(monkeypatch):
    """Webhook for an unregistered connector -> 404 (KeyError), no user gate."""
    for role in (None, "member", "owner", "collaborator", "superadmin"):
        with TestClient(_matrix_app(role, monkeypatch)) as client:
            resp = client.post(
                "/api/connectors/not-registered/webhook",
                params={"secret": "anything"},
                json={"text": "hi"},
            )
            assert resp.status_code == 404, (
                f"role={role} unregistered webhook: expected 404, got {resp.status_code}"
            )