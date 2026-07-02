"""Prometheus /metrics endpoint.

Returns the in-process Counter / Gauge registry in Prometheus text
exposition format. No auth — scrape this from a private network.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.gateway.observability.metrics import render_prometheus

router = APIRouter(prefix="/api")


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(
        content=render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
