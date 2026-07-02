"""Tests for Prometheus /metrics endpoint + render_prometheus()."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.observability.metrics import (
    Counter,
    Gauge,
    render_prometheus,
)
from app.gateway.observability.routers.metrics import router


def test_render_prometheus_includes_counter():
    c = Counter("test_requests_total", "test counter")
    c.inc()
    out = render_prometheus()
    assert "test_requests_total" in out
    assert "# TYPE test_requests_total counter" in out


def test_render_prometheus_includes_gauge():
    g = Gauge("test_queue_depth", "test gauge")
    g.set(42.0)
    out = render_prometheus()
    assert "test_queue_depth" in out
    assert "42" in out
    assert "# TYPE test_queue_depth gauge" in out


def test_metrics_endpoint():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
