"""Tests for the observability surface (no-op when disabled)."""
from __future__ import annotations

import pytest

from app.gateway.observability.langfuse_exporter import (
    export_span,
    is_enabled as langfuse_enabled,
)
from app.gateway.observability.metrics import Counter, Gauge
from app.gateway.observability.tracing import (
    get_current_trace_id,
    init_tracing,
    is_enabled as tracing_enabled,
    span,
)


# ---------------------------------------------------------------- tracing
def test_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MICX_OBSERVABILITY_ENABLED", raising=False)
    init_tracing()  # force re-read env
    assert tracing_enabled() is False
    assert get_current_trace_id() is None


def test_tracing_span_is_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("MICX_OBSERVABILITY_ENABLED", raising=False)
    init_tracing()
    with span("test") as _:
        # No exception, no trace id set
        assert get_current_trace_id() is None


def test_tracing_enabled_via_env(monkeypatch):
    monkeypatch.setenv("MICX_OBSERVABILITY_ENABLED", "true")
    init_tracing(enabled=True)  # force re-read after env mutation
    assert tracing_enabled() is True


def test_tracing_span_sets_trace_id_when_enabled(monkeypatch):
    monkeypatch.setenv("MICX_OBSERVABILITY_ENABLED", "true")
    init_tracing(enabled=True)
    assert get_current_trace_id() is None
    with span("my-span"):
        assert get_current_trace_id() == "my-span"
    assert get_current_trace_id() is None  # cleared on exit


# ---------------------------------------------------------------- langfuse
def test_langfuse_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MICX_LANGFUSE_ENABLED", raising=False)
    assert langfuse_enabled() is False
    # export_span should be a no-op
    export_span("ignored", {"key": "value"})  # no exception


# ---------------------------------------------------------------- metrics
def test_counter_increments():
    c = Counter("test_counter_inc")
    c.reset()
    c.inc()
    c.inc(2)
    assert c.value == 3


def test_counter_rejects_negative():
    c = Counter("test_counter_neg")
    c.reset()
    with pytest.raises(ValueError, match="non-negative"):
        c.inc(-1)


def test_gauge_set_and_increment():
    g = Gauge("test_gauge_set")
    g.reset()
    g.set(10)
    g.inc(5)
    assert g.value == 15
    g.dec(3)
    assert g.value == 12


def test_metrics_isolated_by_name():
    a = Counter("a")
    b = Counter("b")
    a.reset()
    b.reset()
    a.inc(5)
    assert a.value == 5
    assert b.value == 0
