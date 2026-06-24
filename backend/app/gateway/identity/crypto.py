"""Symmetric encryption for IdP client secrets.

Uses Fernet (AES-128-CBC + HMAC-SHA256) for authenticated encryption.
Key derived from MICX_SECRET_ENCRYPTION_KEY env var.
"""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


MIN_KEY_BYTES = 32


@dataclass(frozen=True)
class EncryptedValue:
    """Encrypted secret with IV and authentication tag."""
    ciphertext: str  # base64
    iv: str          # base64
    tag: str         # base64


def _get_fernet() -> Fernet:
    """Derive Fernet key from env. Key must be ≥32 bytes when decoded."""
    raw = os.getenv("MICX_SECRET_ENCRYPTION_KEY", "")
    if not raw:
        raise ValueError(
            "MICX_SECRET_ENCRYPTION_KEY is required. Generate with: "
            "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"`"
        )
    if len(raw.encode("utf-8")) < MIN_KEY_BYTES:
        raise ValueError(
            f"MICX_SECRET_ENCRYPTION_KEY must be at least {MIN_KEY_BYTES} bytes "
            f"(got {len(raw.encode('utf-8'))} bytes)"
        )
    # Derive a 32-byte key via SHA-256, then urlsafe-base64 encode for Fernet
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> EncryptedValue:
    """Encrypt plaintext using Fernet. Returns EncryptedValue with IV/tag extracted."""
    if not plaintext:
        raise ValueError("plaintext must not be empty")
    fernet = _get_fernet()
    token = fernet.encrypt(plaintext.encode("utf-8"))
    # Fernet token is base64(version || ts || iv || ciphertext || hmac)
    # Split to expose iv and a synthetic "tag" (the trailing hmac)
    decoded = base64.urlsafe_b64decode(token)
    version, ts, iv, ciphertext, hmac = decoded[1:9], None, decoded[9:25], None, None
    # Simpler: keep token as ciphertext, derive iv from first 16 bytes after version
    iv_bytes = decoded[9:25]
    hmac_bytes = decoded[-32:]
    return EncryptedValue(
        ciphertext=token.decode("ascii"),
        iv=base64.urlsafe_b64encode(iv_bytes).decode("ascii"),
        tag=base64.urlsafe_b64encode(hmac_bytes).decode("ascii"),
    )


def decrypt_secret(encrypted: EncryptedValue) -> str:
    """Decrypt EncryptedValue back to plaintext."""
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted.ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("decryption failed: invalid token or wrong key") from e