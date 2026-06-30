"""Observability package — tracing, metrics, langfuse export.

All public functions in this package are safe to call when observability
is disabled (the default). Production deployments enable it via env
`MICX_OBSERVABILITY_ENABLED=true`.
"""
