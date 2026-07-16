"""Cross-process rotate lock tests for v1.6.2 admin secrets M2.1.

The cross-process lock is the second layer of defense behind the
in-process ``threading.Lock``. It uses ``fcntl.flock`` (POSIX) with a
``msvcrt`` fallback for Windows; in environments that lack both, the
context manager yields ``False`` and the caller must refuse the rotate.
"""

from __future__ import annotations

import base64
import hashlib
import secrets as _pysecrets
import threading
import time

from deerflow.admin.secrets import _acquire_rotate_lock
from deerflow.config.paths import Paths


def _gen_str(length: int = 48) -> str:
    return _pysecrets.token_urlsafe(length)


def _fresh_cipher_key() -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(_gen_str(48).encode()).digest()).decode()


def _patch_paths(monkeypatch, tmp_path):
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr("deerflow.admin.secrets.get_paths", lambda: paths)
    return paths


def test_lock_path_lives_alongside_vault(monkeypatch, tmp_path):
    paths = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())
    with _acquire_rotate_lock():
        lock_path = paths.admin_dir / ".rotate.lock"
        assert lock_path.exists()


def test_lock_released_after_context_exit(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())
    with _acquire_rotate_lock() as cross_proc:
        assert cross_proc is True
    # After exit, a new acquirer should succeed (lock released).
    with _acquire_rotate_lock() as cross_proc2:
        assert cross_proc2 is True


def test_second_acquirer_blocks_while_first_holds(monkeypatch, tmp_path):
    """Two threads hitting ``_acquire_rotate_lock`` serialize — the
    second waits until the first releases. This is the whole point of
    the cross-process lock: prevent two gateway replicas from racing
    the cipher swap.
    """
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())

    events: list[tuple[str, float]] = []
    lock_acquired = threading.Event()
    can_release = threading.Event()

    def holder() -> None:
        with _acquire_rotate_lock():
            events.append(("holder.acquire", time.monotonic()))
            lock_acquired.set()
            # Hold until the main thread signals release.
            can_release.wait(timeout=5)
            events.append(("holder.release", time.monotonic()))

    def waiter() -> None:
        # Wait until holder has the lock, then try to acquire (will block).
        lock_acquired.wait(timeout=5)
        with _acquire_rotate_lock():
            events.append(("waiter.acquire", time.monotonic()))

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=waiter)
    t1.start()
    t2.start()
    # Give holder enough time to enter its critical section.
    assert lock_acquired.wait(timeout=5), "holder never acquired"
    # Wait for waiter to block on the lock; then release holder.
    time.sleep(0.2)
    can_release.set()
    t1.join(timeout=5)
    t2.join(timeout=5)

    acquire_events = [e for e in events if e[0].endswith(".acquire")]
    assert len(acquire_events) == 2
    assert acquire_events[0][0] == "holder.acquire"
    assert acquire_events[1][0] == "waiter.acquire"
    holder_release = next(t for n, t in events if n == "holder.release")
    assert acquire_events[1][1] >= holder_release, "waiter must not acquire before holder releases"


def test_no_os_primitive_returns_false(monkeypatch, tmp_path):
    """Without ``fcntl`` or ``msvcrt`` (or both shadowed), the lock
    context yields ``False`` so the caller can refuse to rotate rather
    than silently corrupt the vault.
    """
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("MICX_ADMIN_SECRET_KEY", _fresh_cipher_key())

    import builtins

    real_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in ("fcntl", "msvcrt"):
            raise ModuleNotFoundError(f"simulated missing {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with _acquire_rotate_lock() as cross_proc:
        assert cross_proc is False