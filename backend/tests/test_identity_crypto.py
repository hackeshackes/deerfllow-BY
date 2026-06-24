import os
import pytest
from app.gateway.identity.crypto import encrypt_secret, decrypt_secret, EncryptedValue

def test_encrypt_then_decrypt_roundtrip():
    plain = "my-client-secret-12345"
    encrypted = encrypt_secret(plain)
    assert isinstance(encrypted, EncryptedValue)
    assert encrypted.ciphertext != plain
    assert decrypt_secret(encrypted) == plain

def test_encrypted_value_has_iv_and_tag():
    encrypted = encrypt_secret("test")
    assert encrypted.iv  # non-empty
    assert encrypted.tag  # non-empty

def test_decrypt_with_wrong_key_fails(monkeypatch):
    encrypted = encrypt_secret("test")
    monkeypatch.setenv("MICX_SECRET_ENCRYPTION_KEY", "different-key-of-same-length-32b")
    # Force re-import to pick up new key
    import importlib
    from app.gateway.identity import crypto
    importlib.reload(crypto)
    with pytest.raises(ValueError, match="decryption failed"):
        crypto.decrypt_secret(encrypted)

def test_key_must_be_at_least_32_bytes(monkeypatch):
    monkeypatch.setenv("MICX_SECRET_ENCRYPTION_KEY", "short")
    import importlib
    from app.gateway.identity import crypto
    importlib.reload(crypto)
    with pytest.raises(ValueError, match="at least 32 bytes"):
        crypto.encrypt_secret("test")
