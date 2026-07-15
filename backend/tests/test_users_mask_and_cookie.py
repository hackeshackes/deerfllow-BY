"""V08 + V10 + V11 — Tests for ``app.gateway.routers.users`` security helpers.

Covers:

- ``_mask_email`` — non-owners see a partially masked email.
- ``_use_secure_cookie`` — ``BY_FORCE_SECURE_COOKIE`` overrides the
  ``X-Forwarded-Proto`` header (the V11 spoofing vulnerability).
- ``include_invite`` query param — invite token must NOT leak into the default
  ``GET /api/users/{id}`` response, only when explicitly opted in.
"""

from __future__ import annotations

import pytest

from app.gateway.routers.users import _mask_email, _use_secure_cookie


# ---------------------------------------------------------------------------
# _mask_email
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "email, expected",
    [
        ("john.doe@example.com", "j******e@example.com"),
        ("a@example.com", "a*@example.com"),
        ("ab@example.com", "a*@example.com"),  # len <= 2 branch
        ("verylongusername@example.com", "v**************e@example.com"),
        ("", ""),
        ("no-at-sign", "no-at-sign"),
    ],
)
def test_mask_email_known_cases(email: str, expected: str) -> None:
    assert _mask_email(email) == expected


def test_mask_email_handles_empty() -> None:
    assert _mask_email("") == ""


# ---------------------------------------------------------------------------
# _use_secure_cookie
# ---------------------------------------------------------------------------


def _request_with_proto(proto: str | None):
    """Build a minimal request stub with the X-Forwarded-Proto header set."""

    class _StubHeaders:
        def __init__(self, proto: str | None) -> None:
            self._proto = proto

        def get(self, key: str, default: str = "") -> str:
            if key.lower() == "x-forwarded-proto" and self._proto is not None:
                return self._proto
            return default

    class _StubRequest:
        def __init__(self, proto: str | None) -> None:
            self.headers = _StubHeaders(proto)

    return _StubRequest(proto)


def test_use_secure_cookie_default_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BY_FORCE_SECURE_COOKIE", raising=False)
    assert _use_secure_cookie() is False
    assert _use_secure_cookie(_request_with_proto(None)) is False


def test_use_secure_cookie_honors_https_forwarded_proto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BY_FORCE_SECURE_COOKIE", raising=False)
    assert _use_secure_cookie(_request_with_proto("https")) is True


def test_use_secure_cookie_ignores_http_forwarded_proto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BY_FORCE_SECURE_COOKIE", raising=False)
    assert _use_secure_cookie(_request_with_proto("http")) is False


@pytest.mark.parametrize("flag_value", ["1", "true", "True", "yes", "YES"])
def test_use_secure_cookie_env_forces_secure(
    monkeypatch: pytest.MonkeyPatch, flag_value: str
) -> None:
    """V11 — operator opt-in must override any header state, including a
    spoofed ``X-Forwarded-Proto: https`` from an attacker on the same network.
    """
    monkeypatch.setenv("BY_FORCE_SECURE_COOKIE", flag_value)
    assert _use_secure_cookie() is True
    assert _use_secure_cookie(_request_with_proto("http")) is True
    assert _use_secure_cookie(_request_with_proto("https")) is True


@pytest.mark.parametrize("flag_value", ["0", "false", "off", ""])
def test_use_secure_cookie_env_falsy_does_not_force_secure(
    monkeypatch: pytest.MonkeyPatch, flag_value: str
) -> None:
    monkeypatch.setenv("BY_FORCE_SECURE_COOKIE", flag_value)
    assert _use_secure_cookie() is False


# ---------------------------------------------------------------------------
# include_invite — invite token must not leak in default GET responses
# ---------------------------------------------------------------------------


def test_to_user_response_omits_invite_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """V10 — ensure the default ``_to_user_response`` does NOT include the
    invite token unless ``include_invite=True`` is passed.
    """
    from datetime import UTC, datetime, timedelta

    from app.gateway.routers.users import (
        AuthUser,
        InviteToken,
        _to_user_response,
    )

    invited_user = AuthUser(
        id="u-1",
        email="pending@example.com",
        name="Pending",
        role="member",
        status="invited",
        password_hash="x",
        salt="x",
        invited_at=datetime.now(UTC).isoformat(),
        activated_at=None,
        last_login_at=None,
    )
    invite = InviteToken(
        id="inv-1",
        user_id="u-1",
        token="super-secret-token-12345",
        expires_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        used_at=None,
        created_at=datetime.now(UTC).isoformat(),
    )
    monkeypatch.setattr(
        "app.gateway.routers.users.get_active_invite_for_user",
        lambda user_id: invite if user_id == "u-1" else None,
    )

    response = _to_user_response(invited_user, include_invite=False)
    assert response.invite is None

    response_with_token = _to_user_response(invited_user, include_invite=True)
    assert response_with_token.invite is not None
    assert response_with_token.invite.token == "super-secret-token-12345"


def test_to_user_response_includes_invite_only_for_invited_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the user is already active, include_invite=True must NOT surface a
    stale token.
    """
    from datetime import UTC, datetime, timedelta

    from app.gateway.routers.users import (
        AuthUser,
        InviteToken,
        _to_user_response,
    )

    active_user = AuthUser(
        id="u-2",
        email="active@example.com",
        name="Active",
        role="member",
        status="active",
        password_hash="x",
        salt="x",
        invited_at=datetime.now(UTC).isoformat(),
        activated_at=datetime.now(UTC).isoformat(),
        last_login_at=datetime.now(UTC).isoformat(),
    )
    # Even though an invite technically exists in the store, it must not
    # surface when the user has already activated.
    stale = InviteToken(
        id="inv-2",
        user_id="u-2",
        token="should-never-be-returned",
        expires_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        used_at=None,
        created_at=datetime.now(UTC).isoformat(),
    )
    monkeypatch.setattr(
        "app.gateway.routers.users.get_active_invite_for_user",
        lambda user_id: stale if user_id == "u-2" else None,
    )

    response = _to_user_response(active_user, include_invite=True)
    assert response.invite is None