from __future__ import annotations

import base64
import contextlib
import datetime as _dt
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

SECRET_REF_PREFIX = "secret://"
_DEV_AUTH_SECRET = "by-local-dev-secret"
_ENV_FLAG_DEV_ALLOWED = "BY_ALLOW_DEV_AUTH_SECRET"
_secret_lock = Lock()


# ---------------------------------------------------------------------------
# Catalog of well-known secrets (env-only; cannot live in vault)
# ---------------------------------------------------------------------------
# These names are typically resolved via ``os.getenv`` at request time. The
# ``SECRETS_VAULT_ROUTABLE`` subset is what the ``/api/admin/secrets/{rotate,
# status}`` endpoints surface; the rest are exposed via ``GET /secrets/status``
# only when ``include_all=true``.

KNOWN_SECRET_KEYS: tuple[str, ...] = (
    "BETTER_AUTH_SECRET",
    "MICX_ADMIN_SECRET_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "GOOGLE_API_KEY",
    "ALIYUN_API_KEY",
    "VOLCENGINE_API_KEY",
    "MOONSHOT_API_KEY",
    "TAVILY_API_KEY",
    "JINA_API_KEY",
    "INFOQUEST_API_KEY",
    "FIRECRAWL_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_BASE_URL",
    "DEER_FLOW_HOME",
    "DEER_FLOW_CONFIG_PATH",
    "DEER_FLOW_EXTENSIONS_CONFIG_PATH",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_PROJECT",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_HOST",
)


# ---------------------------------------------------------------------------
# Catalog of well-known vault-routed secrets (stored in backend/.deer-flow/admin/
# secrets.enc). Mirrors ``models.override.yaml`` ``secret://`` references.
# ---------------------------------------------------------------------------
KNOWN_VAULT_KEYS: tuple[str, ...] = (
    "models/dspark-v1.1-mida-brikie/api_key",
    "models/mixh-coder/api_key",
    "models/Qwen3-5-35B-A3B-Claude-4-6-Opus-Reasoning/api_key",
    "models/MicX Service/api_key",
    "models/local-openai-placeholder/api_key",
)


# Catalog of keys the ``/api/admin/secrets/rotate`` endpoint will accept.
# Anything outside this set must be rotated by editing ``.env`` (or
# ``docker/.env``) and restarting the gateway. Vendor API keys injected
# from MCP config stay env-only by design — those credentials are owned
# by the connector lifecycle, not the admin vault.
SECRETS_VAULT_ROUTABLE: frozenset[str] = frozenset(
    {
        # Auth / cipher — rotating these is exactly the self-lockout
        # scenario the password re-verification on /rotate guards against.
        "BETTER_AUTH_SECRET",
        "MICX_ADMIN_SECRET_KEY",
        # Production vault-routed model keys.
        "models/dspark-v1.1-mida-brikie/api_key",
        "models/mixh-coder/api_key",
        "models/Qwen3-5-35B-A3B-Claude-4-6-Opus-Reasoning/api_key",
        "models/MicX Service/api_key",
    }
)


# Heuristic for "this value isn't a real credential". Used by the
# ``/api/admin/secrets/status`` endpoint to surface missing or placeholder
# keys to operators. Real production keys are long, high-entropy strings that
# almost never match these patterns.
_PLACEHOLDER_PATTERN = re.compile(
    r"(?i)\A("
    r"changeme|placeholder|change-?me|"
    r"sk-local-placeholder|xxx+|todo|sample|example|"
    r"replace-?me-?with-?|"
    r"enter-?your-?|your-?key-?here|"
    r"test-?key-?123|"
    r"foo|bar|baz|00000000"
    r")\Z|.*change.*me.*"
)


def is_placeholder_value(value: str | None) -> bool:
    """Return ``True`` when ``value`` is empty, whitespace, or matches a known placeholder."""
    if not value:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.lower() == "changeme":
        return True
    return _PLACEHOLDER_PATTERN.match(stripped) is not None


def delete_secret(key: str) -> bool:
    """Remove ``key`` from the encrypted vault.

    Returns ``True`` when the key was present and removed, ``False`` otherwise.
    """
    normalized = key.strip().strip("/")
    if not normalized:
        raise ValueError("Secret key path cannot be empty.")
    with _secret_lock:
        data = _read_secret_map()
        if normalized not in data:
            return False
        del data[normalized]
        _write_secret_map(data)
    return True


def get_vault_mtime() -> _dt.datetime | None:
    """Return the last-modified timestamp of the encrypted vault file, or ``None`` when missing."""
    path = _vault_path()
    if not path.exists():
        return None
    return _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.UTC)


def rotate_env_secret(env_key: str, new_value: str) -> list[str]:
    """Replace ``os.environ[env_key]`` and report which subsystems must invalidate caches.

    The function writes the new value in-process (``os.environ``) so the next
    ``_vault_cipher()`` or ``_auth_secret()`` invocation reads it. It does not
    modify ``.env`` or ``docker/.env`` — those are owned by M3 (rebuild).

    Returns the cascade list (see PRD):
      * ``["session_hmac", "vault_cipher"]`` — for ``BETTER_AUTH_SECRET`` or
        ``MICX_ADMIN_SECRET_KEY``, both the session HMAC verifier and the vault
        cipher are derived from the rotated key.
      * ``[]`` — for any other secret (caller is responsible for any cache
        invalidation downstream).
    """
    if not env_key or not isinstance(env_key, str):
        raise ValueError("env_key must be a non-empty string.")
    if not isinstance(new_value, str):
        raise ValueError("new_value must be a string.")
    os.environ[env_key] = new_value
    if env_key in {"BETTER_AUTH_SECRET", "MICX_ADMIN_SECRET_KEY"}:
        return ["session_hmac", "vault_cipher"]
    return []


def rotate_vault_cipher(old_env_value: str, new_env_value: str) -> None:
    """Re-encrypt the on-disk vault with ``new_env_value``'s derived cipher.

    The caller is responsible for taking a snapshot of the current cipher's
    derived key (``old_env_value``) before swapping the env var. The vault is
    read using the *old* cipher, then written using the *new* cipher — atomic
    via the standard ``tempfile + Path.replace`` pattern.

    Empty vault (no entries) is a no-op.
    """
    if not isinstance(old_env_value, str) or not isinstance(new_env_value, str):
        raise ValueError("old_env_value and new_env_value must both be strings.")

    def _derive(value: str) -> Fernet:
        from cryptography.fernet import Fernet
        derived = hashlib.sha256(value.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(derived))

    path = _vault_path()
    if not path.exists():
        return
    payload = path.read_bytes()
    if not payload:
        return

    old_cipher = _derive(old_env_value or os.getenv(_ENV_FLAG_DEV_ALLOWED, ""))
    # The dev-fallback path is normally not relevant here; the caller must
    # pass the literal env value they observed before the swap.
    try:
        plaintext = old_cipher.decrypt(payload)
    except Exception as exc:
        raise RuntimeError("Failed to decrypt admin secrets vault with old cipher.") from exc
    data = json.loads(plaintext.decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Admin secrets vault is corrupted during cipher rotation.")

    new_cipher = _derive(new_env_value)
    new_payload = new_cipher.encrypt(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_bytes(new_payload)
    temp_path.replace(path)


def is_secret_ref(value: str | None) -> bool:
    return bool(value and value.startswith(SECRET_REF_PREFIX))


def _secret_key_name(ref_key: str) -> str:
    return ref_key.removeprefix(SECRET_REF_PREFIX)


# ---------------------------------------------------------------------------
# Cross-process lock for atomic rotate
# ---------------------------------------------------------------------------
# The in-process ``_secret_lock`` guards ``upsert_secret`` /
# ``delete_secret`` / ``_read_secret_map`` from thread races inside one
# Python interpreter. It does NOT protect against two gateway replicas
# pointing at the same vault — that needs an OS-level lock so the second
# rotate blocks instead of racing the cipher swap and losing the read
# path. Mirrors the pattern in
# ``deerflow.community.aio_sandbox.aio_sandbox_provider``: POSIX flock
# with a ``msvcrt`` fallback for Windows. Yields ``True`` when the OS
# lock primitive was acquired, ``False`` otherwise (test environments
# without ``fcntl``/``msvcrt``).


@contextlib.contextmanager
def _acquire_rotate_lock() -> Any:
    """Hold an exclusive cross-process lock for the duration of a rotate.

    Blocks if another process holds the lock (POSIX). On Linux this is a
    blocking ``flock``; on Windows we use ``msvcrt.locking`` with the same
    semantics. Yields ``True`` when the lock was acquired, ``False`` when
    the OS doesn't expose either primitive (test environments that don't
    have ``fcntl``/``msvcrt``) — callers should fall back to the
    in-process ``_secret_lock`` and accept the cross-process race.
    """
    lock_path = _vault_path().parent / ".rotate.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield True
            return
        except (ImportError, ModuleNotFoundError):
            pass
        try:
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            yield True
            return
        except (ImportError, ModuleNotFoundError):
            pass
        # No OS lock primitive available — rely on in-process serialization
        # only. Better than failing closed in odd environments.
        yield False
    finally:
        lock_file.close()


def _is_dev_secret_allowed() -> bool:
    """Mirror of app.gateway.auth._is_dev_secret_allowed.

    Production must never use the dev default; otherwise the Fernet vault
    becomes decryptable by anyone who knows the well-known string.
    """
    if os.getenv("ENV", "").lower() == "production":
        return False
    return os.getenv(_ENV_FLAG_DEV_ALLOWED, "").lower() in {"1", "true", "yes"}


def _vault_cipher() -> Fernet:
    try:
        from cryptography.fernet import Fernet
    except ModuleNotFoundError as exc:
        raise RuntimeError("cryptography is required for admin secret storage. Install backend dependencies first.") from exc
    raw_secret = os.getenv("MICX_ADMIN_SECRET_KEY") or os.getenv("BETTER_AUTH_SECRET")
    if not raw_secret:
        if _is_dev_secret_allowed():
            logger.warning(
                "MICX_ADMIN_SECRET_KEY and BETTER_AUTH_SECRET are unset; using development fallback for the admin vault. "
                "This is insecure and only allowed when BY_ALLOW_DEV_AUTH_SECRET=1 is set outside of production."
            )
            raw_secret = _DEV_AUTH_SECRET
        else:
            raise RuntimeError(
                "MICX_ADMIN_SECRET_KEY (or BETTER_AUTH_SECRET) is required to encrypt the admin vault. "
                "Generate a strong secret (e.g. `openssl rand -base64 32`) before starting the server."
            )
    elif raw_secret == _DEV_AUTH_SECRET and not _is_dev_secret_allowed():
        raise RuntimeError(
            "MICX_ADMIN_SECRET_KEY/BETTER_AUTH_SECRET is set to the well-known development default. "
            "Generate a strong secret and update the environment. "
            "To keep the dev default, set BY_ALLOW_DEV_AUTH_SECRET=1."
        )
    derived = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def _vault_path() -> Path:
    return get_paths().admin_secrets_file


def _read_secret_map() -> dict[str, str]:
    path = _vault_path()
    if not path.exists():
        return {}
    payload = path.read_bytes()
    if not payload:
        return {}
    try:
        decrypted = _vault_cipher().decrypt(payload)
    except Exception:
        # Vault exists but can't be decrypted (e.g. cipher key env var not set
        # during config loading). Treat as empty — the next upsert will
        # re-encrypt under the correct key.
        return {}
    data = json.loads(decrypted.decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Admin secrets vault is corrupted.")
    return {str(key): str(value) for key, value in data.items()}


def _write_secret_map(values: dict[str, str]) -> None:
    path = _vault_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _vault_cipher().encrypt(json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    # Use a per-call unique temp file so concurrent writers don't clobber
    # each other's ciphertext-in-flight on a fixed ``.tmp`` name.
    import tempfile

    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(encrypted)
        Path(temp_name).replace(path)
    except BaseException:  # noqa: BLE001 — atomic-write best-effort cleanup
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def upsert_secret(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("$") or is_secret_ref(value):
        return value
    normalized_key = key.strip().strip("/")
    if not normalized_key:
        raise ValueError("Secret key path cannot be empty.")
    with _secret_lock:
        data = _read_secret_map()
        data[normalized_key] = value
        _write_secret_map(data)
    return f"{SECRET_REF_PREFIX}{normalized_key}"


def resolve_secret_ref(value: str | None) -> str | None:
    if value is None or not is_secret_ref(value):
        return value
    with _secret_lock:
        data = _read_secret_map()
    key = _secret_key_name(value)
    return data.get(key)


def mask_secret_value(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("$"):
        return value
    if is_secret_ref(value):
        return "••••••••"
    if len(value) <= 4:
        return "•" * len(value)
    return f"{value[:2]}{'•' * max(len(value) - 4, 4)}{value[-2:]}"
