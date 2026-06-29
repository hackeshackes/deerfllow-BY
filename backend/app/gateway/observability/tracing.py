"""Tracing abstraction — OpenTelemetry-ready, disabled by default.

The API mirrors the subset of OpenTelemetry that we actually use, so
swapping in the real OTel SDK is a one-import change. Until then, all
operations are no-ops and `get_current_trace_id()` returns `None`.
"""
from __future__ import annotations

import os
import threading
from typing import Iterator
from contextlib import contextmanager

_state_lock = threading.Lock()
_enabled: bool = os.environ.get("MICX_OBSERVABILITY_ENABLED", "").lower() == "true"
# Single-slot trace id storage; replaced on every span start.
_current_trace_id: str | None = None


def init_tracing(enabled: bool | None = None) -> None:
    """Override the default tracing-enabled flag (mainly for tests)."""
    global _enabled
    if enabled is not None:
        with _state_lock:
            _enabled = enabled


def is_enabled() -> bool:
    with _state_lock:
        return _enabled


def get_current_trace_id() -> str | None:
    with _state_lock:
        return _current_trace_id


@contextmanager
def span(name: str) -> Iterator[None]:
    """Open a span. When tracing is disabled this is a no-op context manager.

    When enabled (production), replace this body with the real OTel SDK
    span() context. The interface is the same.
    """
    global _current_trace_id
    if not is_enabled():
        yield
        return
    with _state_lock:
        _current_trace_id = name  # placeholder — real OTel gives a UUID
    try:
        yield
    finally:
        with _state_lock:
            _current_trace_id = None
