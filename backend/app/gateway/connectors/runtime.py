"""Connector runtime — execute `send`, retry on failure, route to DLQ.

The runtime owns the retry policy and the dead-letter queue. It is intentionally
separate from the in-process `ConnectorRegistry` so that a runtime can be
reconfigured (different retry budgets, DLQ store) without touching registration.

Retry semantics: linear backoff with a configurable `retry_delay` (use 0 in
tests). Up to `max_retries` additional attempts are made after the initial
send. The first success short-circuits the loop. If every attempt fails, a
`DLQEntry` is appended to the in-memory DLQ (unless disabled).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .base import BaseConnector, ConnectorMessage, ConnectorResponse


@dataclass
class DLQEntry:
    """A message that exhausted all retries."""

    connector: str
    message: ConnectorMessage
    last_error: str
    attempts: int
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RuntimeResponse:
    """Result of `ConnectorRuntime.send`."""

    success: bool
    external_id: str | None = None
    error: str | None = None
    attempts: int = 0
    dlq: DLQEntry | None = None
    responses: list[ConnectorResponse] = field(default_factory=list)
    """All per-attempt responses — useful for debugging flaky connectors."""


class ConnectorRuntime:
    """Send messages through a registered connector with retry + DLQ."""

    def __init__(
        self,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        dlq_enabled: bool = True,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if retry_delay < 0:
            raise ValueError("retry_delay must be >= 0")

        self._connectors: dict[str, BaseConnector] = {}
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._dlq_enabled = dlq_enabled
        self._dlq: list[DLQEntry] = []

    # ------------------------------------------------------------------ registry
    def register(self, connector: BaseConnector) -> None:
        if not connector.name:
            raise ValueError("connector.name must be set before registration")
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> None:
        self._connectors.pop(name, None)

    # ----------------------------------------------------------------------- api
    async def send(
        self, connector_name: str, message: ConnectorMessage
    ) -> RuntimeResponse:
        if connector_name not in self._connectors:
            return RuntimeResponse(
                success=False,
                error=f"unknown connector: {connector_name!r}",
                attempts=0,
            )
        connector = self._connectors[connector_name]
        last_error = ""
        responses: list[ConnectorResponse] = []
        total_attempts = self._max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                resp = await connector.send(message)
            except Exception as e:  # noqa: BLE001 — we want to capture all errors
                last_error = f"{type(e).__name__}: {e}"
                responses.append(ConnectorResponse(success=False, error=last_error))
            else:
                responses.append(resp)
                if resp.success:
                    return RuntimeResponse(
                        success=True,
                        external_id=resp.external_id,
                        attempts=attempt,
                        responses=responses,
                    )
                last_error = resp.error or "unknown"

            if attempt < total_attempts and self._retry_delay > 0:
                await asyncio.sleep(self._retry_delay)

        # Every attempt failed — route to DLQ if enabled
        dlq_entry: DLQEntry | None = None
        if self._dlq_enabled:
            dlq_entry = DLQEntry(
                connector=connector_name,
                message=message,
                last_error=last_error,
                attempts=total_attempts,
            )
            self._dlq.append(dlq_entry)
        return RuntimeResponse(
            success=False,
            error=last_error,
            attempts=total_attempts,
            dlq=dlq_entry,
            responses=responses,
        )

    # --------------------------------------------------------------------- DLQ
    def get_dlq(self) -> list[DLQEntry]:
        return list(self._dlq)

    def clear_dlq(self) -> int:
        n = len(self._dlq)
        self._dlq.clear()
        return n
