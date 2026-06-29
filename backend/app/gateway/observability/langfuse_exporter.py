"""Langfuse export — disabled-by-default stub.

The real exporter would subscribe to OpenTelemetry spans and push them
to the Langfuse ingestion endpoint. Until the OpenTelemetry integration
is wired in (Task 5 of the v1.5.8 plan), this module only exposes
the configuration surface so the rest of the app can import safely.
"""
from __future__ import annotations

import os


def is_enabled() -> bool:
    return os.environ.get("MICX_LANGFUSE_ENABLED", "").lower() == "true"


def export_span(span_name: str, attributes: dict | None = None) -> None:
    """No-op when Langfuse is disabled. Real impl posts to Langfuse SDK."""
    if not is_enabled():
        return
    # The real implementation will:
    #   langfuse_context.update_current_observation(name=span_name, metadata=attributes)
    # For v1.5.8 MVP we only ship the configuration surface.
