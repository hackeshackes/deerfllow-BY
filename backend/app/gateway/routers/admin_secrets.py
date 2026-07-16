"""Owner-only admin endpoints for the encrypted secrets vault.

Three endpoints:
- ``POST /api/admin/secrets/upsert`` — create or replace a vault entry.
- ``POST /api/admin/secrets/rotate`` — atomic env + vault rewrite, gated by
  ``current_admin_password`` for keys that affect auth or the vault cipher.
- ``GET /api/admin/secrets/status`` — report placeholder / fresh / missing for
  every catalog key.

All three mirror the imperative ``require_owner_user(request)`` pattern used
by ``admin_config.py`` so existing tests continue to apply without rewriting.
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from app.gateway.auth import authenticate_user, require_owner_user
from deerflow.admin import (
    KNOWN_SECRET_KEYS,
    KNOWN_VAULT_KEYS,
    SECRETS_VAULT_ROUTABLE,
    append_admin_audit_record,
    delete_secret,
    filter_admin_audit_records,
    get_vault_mtime,
    is_placeholder_value,
    mask_secret_value,
    read_admin_audit_records,
    rotate_env_secret,
    rotate_vault_cipher,
    upsert_secret,
)
from deerflow.admin.secrets import _acquire_rotate_lock, _read_secret_map

router = APIRouter(prefix="/api/admin", tags=["admin-secrets"])


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

SecretKeyStr = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9_./\-:]+$"),
]

SecretValueStr = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class SecretUpsertRequest(BaseModel):
    key: SecretKeyStr = Field(
        description="Hierarchical vault key, e.g. models/foo/api_key or mcp/bar/env/API_KEY",
    )
    value: str | None = Field(
        default=None,
        description="Plaintext value, $ENV reference, or secret:// reference; null deletes the entry",
    )


class SecretUpsertResponse(BaseModel):
    key: str
    reference: str | None
    status: Literal["upserted", "deleted"]
    masked: Literal[True] = True


class SecretRotateRequest(BaseModel):
    key: SecretKeyStr = Field(description="Vault key or env var name to rotate")
    new_value: SecretValueStr = Field(description="New plaintext value; vault is rewritten atomically")
    current_admin_password: Annotated[
        str,
        StringConstraints(min_length=1, max_length=512),
    ] = Field(
        description="Owner's current login password; required for every rotate",
    )


class SecretRotateResponse(BaseModel):
    key: str
    reference: str
    masked: Literal[True] = True
    cascades: list[str]
    cookie_invalidation: Literal["forced_relogin", "none"]


class SecretStatusItem(BaseModel):
    key: str
    state: Literal["missing", "placeholder", "fresh", "configured"]
    is_placeholder: bool
    last_rotated_at: str | None
    source: Literal["vault", "env", "seed_default"]
    masked_value: str | None


class SecretStatusResponse(BaseModel):
    items: list[SecretStatusItem]
    known_keys: list[str]
    vault_mtime: str | None


class AdminAuditEvent(BaseModel):
    ts: str
    action: str
    actor_id: str | None
    target: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AdminAuditResponse(BaseModel):
    events: list[AdminAuditEvent]
    action_prefix: str | None
    actor_id: str | None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_PRIVILEGED_KEYS: frozenset[str] = frozenset({"BETTER_AUTH_SECRET", "MICX_ADMIN_SECRET_KEY"})


def _verify_owner_password(password: str) -> None:
    """Re-authenticate the owner via the same path as /api/session/login.

    Used by ``rotate`` to prevent an attacker who hijacked the session from
    rotating ``BETTER_AUTH_SECRET`` and locking the real owner out.
    """
    email = os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")
    user = authenticate_user(email, password)
    if user is None or not user.is_owner:
        raise HTTPException(status_code=401, detail="当前密码不正确")


def _rotate_atomic(key: str, new_value: str) -> tuple[list[str], str | None]:
    """Replace ``key`` in vault and (if env-routable) in ``os.environ``.

    Returns ``(cascades, reference_or_None)``. Order matters:

    1. Snapshot the current cipher's env value so we can re-encrypt the
       on-disk vault under the *old* cipher (the next read after env swap
       will use the *new* cipher, so a write at that point would lose the
       ability to read the existing encrypted payload).
    2. If the key is an env-routable secret, write the new value to
       ``os.environ`` and call ``rotate_vault_cipher(old, new)`` to re-encrypt
       the on-disk vault under the new cipher.
    3. If the key is *not* env-routable, fall back to a plain
       ``upsert_secret`` (vault cipher is unchanged; the new value is just
       stored under the existing cipher).

    Both steps happen inside ``_secret_lock`` so concurrent reads do not see
    a half-decrypted vault. Callers that need cross-process serialization
    wrap this in ``_acquire_rotate_lock()`` — see ``/secrets/rotate``.
    """
    cascades: list[str] = []
    if key == "MICX_ADMIN_SECRET_KEY":
        old_env = os.environ.get("MICX_ADMIN_SECRET_KEY") or os.environ.get("BETTER_AUTH_SECRET")
        os.environ[key] = new_value
        if old_env is not None and old_env != new_value:
            rotate_vault_cipher(old_env, new_value)
        cascades = rotate_env_secret(key, new_value)
    elif key == "BETTER_AUTH_SECRET":
        # Session secret rotation does not change the vault cipher (which is
        # derived from MICX_ADMIN_SECRET_KEY). Just swap the env var.
        cascades = rotate_env_secret(key, new_value)
    reference = upsert_secret(key, new_value)
    return cascades, reference


def _to_status_item(key: str, vault_data: dict[str, str]) -> SecretStatusItem:
    """Classify one key as missing / placeholder / fresh / configured."""
    if key in vault_data:
        value = vault_data[key]
        source: Literal["vault", "env", "seed_default"] = "vault"
    else:
        env_value = os.getenv(key)
        if env_value is None or not env_value.strip():
            return SecretStatusItem(
                key=key,
                state="missing",
                is_placeholder=False,
                last_rotated_at=None,
                source="seed_default",
                masked_value=None,
            )
        value = env_value
        source = "env"

    placeholder = is_placeholder_value(value)
    if placeholder:
        state: Literal["missing", "placeholder", "fresh", "configured"] = "placeholder"
    elif source == "env":
        # Env-routable secrets are always "configured" once present.
        state = "configured"
    else:
        state = "fresh"
    last_rotated = get_vault_mtime().isoformat() if source == "vault" else None
    return SecretStatusItem(
        key=key,
        state=state,
        is_placeholder=placeholder,
        last_rotated_at=last_rotated,
        source=source,
        masked_value=mask_secret_value(value),
    )


# ---------------------------------------------------------------------------
# Rate limit (sliding window per IP for /rotate)
# ---------------------------------------------------------------------------

_ROTATE_RATE_LIMIT_PER_MINUTE = 10
_ROTATE_WINDOW_SECONDS = 60.0
_rotate_hits: dict[str, deque[float]] = {}


def _check_rotate_rate_limit(ip: str) -> None:
    """429 if the same IP has called rotate more than 10 times in the last 60s."""
    bucket = _rotate_hits.setdefault(ip, deque())
    now = time.monotonic()
    cutoff = now - _ROTATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= _ROTATE_RATE_LIMIT_PER_MINUTE:
        retry_after = max(1, int(_ROTATE_WINDOW_SECONDS - (now - bucket[0])))
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/secrets/upsert", response_model=SecretUpsertResponse)
async def upsert_secret_endpoint(body: SecretUpsertRequest, request: Request) -> SecretUpsertResponse:
    """Create or replace a vault entry. ``value=null`` deletes the entry."""
    user = require_owner_user(request)

    if body.value is None:
        deleted = delete_secret(body.key)
        if deleted:
            append_admin_audit_record(
                "admin_secret.deleted",
                actor_id=user.id,
                target=f"secret://{body.key}",
                details={"key": body.key, "reference": None},
            )
        return SecretUpsertResponse(key=body.key, reference=None, status="deleted")

    reference = upsert_secret(body.key, body.value)
    append_admin_audit_record(
        "admin_secret.upserted",
        actor_id=user.id,
        target=reference or body.key,
        details={"key": body.key, "value_length": len(body.value), "reference": reference},
    )
    return SecretUpsertResponse(key=body.key, reference=reference, status="upserted")


@router.post("/secrets/rotate", response_model=SecretRotateResponse)
async def rotate_secret_endpoint(body: SecretRotateRequest, request: Request) -> SecretRotateResponse:
    """Atomic rotation of an env-routable secret or vault entry.

    Requires ``current_admin_password`` to prevent session-hijack self-lockout.
    Only keys in ``SECRETS_VAULT_ROUTABLE`` are accepted through this endpoint;
    others must be rotated by editing ``.env`` and restarting. Held under an
    exclusive cross-process lock so two gateway replicas pointing at the same
    vault serialize instead of racing the cipher swap.
    """
    user = require_owner_user(request)
    client_ip = request.client.host if request.client else "unknown"
    _check_rotate_rate_limit(client_ip)

    _verify_owner_password(body.current_admin_password)

    if body.key not in SECRETS_VAULT_ROUTABLE:
        raise HTTPException(
            status_code=400,
            detail=f"key '{body.key}' is not rotatable via this endpoint; edit .env and restart instead",
        )

    with _acquire_rotate_lock() as cross_proc:
        if cross_proc is False:
            # No OS lock primitive on this platform — we can't safely
            # guarantee serialization. Refuse rather than risk corruption.
            raise HTTPException(
                status_code=503,
                detail="cross-process rotate lock unavailable on this platform; restart gateway solo",
            )
        try:
            cascades, reference = _rotate_atomic(body.key, body.new_value)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    append_admin_audit_record(
        "admin_secret.rotated",
        actor_id=user.id,
        target=reference or body.key,
        details={
            "key": body.key,
            "value_length": len(body.new_value),
            "cascades": cascades,
            "cookie_invalidation": "forced_relogin" if "session_hmac" in cascades else "none",
            "password_verified": True,
        },
    )

    return SecretRotateResponse(
        key=body.key,
        reference=reference or "",
        cascades=cascades,
        cookie_invalidation="forced_relogin" if "session_hmac" in cascades else "none",
    )


@router.get("/secrets/status", response_model=SecretStatusResponse)
async def secrets_status_endpoint(
    request: Request,
    include_all: bool = False,
) -> SecretStatusResponse:
    """Report the current state of every catalog secret.

    By default only catalog entries from ``KNOWN_VAULT_KEYS`` are reported
    (i.e. the operator-visible set). Pass ``?include_all=true`` to also see
    env-only keys (``OPENAI_API_KEY``, ``TAVILY_API_KEY``, ...).
    """
    require_owner_user(request)

    vault_data = _read_secret_map()
    keys: list[str] = list(KNOWN_VAULT_KEYS)
    if include_all:
        keys = sorted(set(KNOWN_VAULT_KEYS) | set(KNOWN_SECRET_KEYS))
    else:
        # Always include privileged keys; they live in env and must be visible.
        for k in _PRIVILEGED_KEYS:
            if k not in keys:
                keys.append(k)

    items = [_to_status_item(k, vault_data) for k in keys]
    mtime = get_vault_mtime()
    return SecretStatusResponse(
        items=items,
        known_keys=keys,
        vault_mtime=mtime.isoformat() if mtime else None,
    )


@router.get("/secrets/audit-events", response_model=AdminAuditResponse)
async def admin_audit_events_endpoint(
    request: Request,
    action_prefix: str | None = None,
    actor_id: str | None = None,
    limit: int = 200,
) -> AdminAuditResponse:
    """Return the recent admin audit log entries (JSONL on disk).

    ``action_prefix`` lets the caller narrow to a subsystem, e.g.
    ``admin_secret.`` to see only vault activity. ``actor_id`` filters
    by the owner who triggered the action. ``limit`` caps the read; the
    underlying file is the truth, so we read the tail and slice.
    """
    require_owner_user(request)

    records = read_admin_audit_records(limit=limit)
    filtered = filter_admin_audit_records(
        records, action_prefix=action_prefix, actor_id=actor_id,
    )
    return AdminAuditResponse(
        events=[
            AdminAuditEvent(
                ts=str(e.get("ts", "")),
                action=str(e.get("action", "")),
                actor_id=e.get("actor_id"),
                target=str(e.get("target", "")),
                details={k: v for k, v in (e.get("details") or {}).items()
                         if isinstance(v, (str, int, float, bool, type(None)))},
            )
            for e in filtered
        ],
        action_prefix=action_prefix,
        actor_id=actor_id,
    )
