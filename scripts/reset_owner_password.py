"""Reset the DeerFlow owner password to ``BY_ADMIN_PASSWORD`` env value.

Use this when the owner password hash in ``backend/.deer-flow/users.json``
drifts from the ``BY_ADMIN_PASSWORD`` env var (typically after a forgotten
password or a manual hash edit). Regenerates salt + PBKDF2-SHA256 (120k
iterations) hash for the owner record only; leaves every other user
untouched.

Usage:
    python scripts/reset_owner_password.py

Reads the env value from the project-root ``.env`` file if present, or
the process environment. Writes the updated ``users.json`` back atomically
(tempfile + Path.replace) so the gateway hot-reloading the file won't
catch a half-written document.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

PBKDF2_ITERATIONS = 120_000


def _load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _hash(password: str, salt_hex: str) -> str:
    # NOTE: matches auth.py:485 — salt is encoded as UTF-8 (NOT bytes.fromhex)
    # because that helper predates the hex migration. The hex form is the
    # on-disk convention (see ``_read_users_payload``); hashing treats it as
    # a string of ASCII characters.
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_hex.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    _load_env(repo_root / ".env")

    password = os.getenv("BY_ADMIN_PASSWORD")
    if not password:
        print("BY_ADMIN_PASSWORD is not set; cannot reset.", file=sys.stderr)
        return 1

    email = os.getenv("BY_ADMIN_EMAIL", "sabar.bao@me.com")
    users_path = repo_root / "backend" / ".deer-flow" / "users.json"
    if not users_path.exists():
        print(f"users.json not found at {users_path}", file=sys.stderr)
        return 1

    data = json.loads(users_path.read_text(encoding="utf-8"))
    owner = next((u for u in data.get("users", []) if u.get("email") == email), None)
    if owner is None:
        print(f"Owner {email} not found in users.json", file=sys.stderr)
        return 1

    new_salt = secrets.token_hex(16)
    owner["salt"] = new_salt
    owner["password_hash"] = _hash(password, new_salt)

    fd, tmp_name = tempfile.mkstemp(prefix="users.", suffix=".json.tmp", dir=str(users_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        Path(tmp_name).replace(users_path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    print(f"reset {email} (id={owner['id']}) to BY_ADMIN_PASSWORD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())