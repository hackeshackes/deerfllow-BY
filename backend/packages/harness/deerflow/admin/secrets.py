from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from threading import Lock

from deerflow.config.paths import get_paths

SECRET_REF_PREFIX = "secret://"
_secret_lock = Lock()


def is_secret_ref(value: str | None) -> bool:
    return bool(value and value.startswith(SECRET_REF_PREFIX))


def _secret_key_name(ref_key: str) -> str:
    return ref_key.removeprefix(SECRET_REF_PREFIX)


def _vault_cipher() -> Fernet:
    try:
        from cryptography.fernet import Fernet
    except ModuleNotFoundError as exc:
        raise RuntimeError("cryptography is required for admin secret storage. Install backend dependencies first.") from exc
    raw_secret = os.getenv("MICX_ADMIN_SECRET_KEY") or os.getenv("BETTER_AUTH_SECRET") or "by-local-dev-secret"
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
    except Exception as exc:
        raise RuntimeError("Failed to decrypt admin secrets vault. Check MICX_ADMIN_SECRET_KEY/BETTER_AUTH_SECRET.") from exc
    data = json.loads(decrypted.decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Admin secrets vault is corrupted.")
    return {str(key): str(value) for key, value in data.items()}


def _write_secret_map(values: dict[str, str]) -> None:
    path = _vault_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _vault_cipher().encrypt(json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    temp_path = path.with_suffix(".tmp")
    temp_path.write_bytes(encrypted)
    temp_path.replace(path)


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
