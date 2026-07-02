"""In-process metrics primitives (Counter, Gauge).

Production swap: replace these with `prometheus_client.Counter` /
`Gauge` and expose them via the standard `/metrics` endpoint. The
in-process variants keep tests deterministic — no Prometheus registry
to clean up between tests.
"""

from __future__ import annotations

import threading
from typing import Dict


_metrics_lock = threading.Lock()
_counters: Dict[str, int] = {}
_gauges: Dict[str, float] = {}


class Counter:
    """Monotonically increasing counter (resets on process restart)."""

    def __init__(self, name: str, help: str = "") -> None:
        self._name = name
        self._help = help

    def inc(self, value: int = 1) -> None:
        if value < 0:
            raise ValueError("Counter.inc requires non-negative value")
        with _metrics_lock:
            _counters[self._name] = _counters.get(self._name, 0) + value

    @property
    def value(self) -> int:
        with _metrics_lock:
            return _counters.get(self._name, 0)

    def reset(self) -> None:
        """For tests only — clears the underlying counter."""
        with _metrics_lock:
            _counters.pop(self._name, None)


class Gauge:
    """Point-in-time value (e.g. queue depth, current connections)."""

    def __init__(self, name: str, help: str = "") -> None:
        self._name = name
        self._help = help

    def set(self, value: float) -> None:
        with _metrics_lock:
            _gauges[self._name] = float(value)

    def inc(self, value: float = 1.0) -> None:
        with _metrics_lock:
            _gauges[self._name] = _gauges.get(self._name, 0.0) + value

    def dec(self, value: float = 1.0) -> None:
        self.inc(-value)

    @property
    def value(self) -> float:
        with _metrics_lock:
            return _gauges.get(self._name, 0.0)

    def reset(self) -> None:
        with _metrics_lock:
            _gauges.pop(self._name, None)


def render_prometheus() -> str:
    """Render all registered metrics in Prometheus text exposition format.

    We use the in-process _counters / _gauges dicts (no prometheus_client
    dependency) so the v1.5.10 build stays slim. The format is the
    subset Prometheus scrapers need:
      # HELP <name> <help>
      # TYPE <name> counter|gauge
      <name> <value>
    """
    with _metrics_lock:
        lines: list[str] = []
        for name, value in sorted(_counters.items()):
            lines.append(f"# HELP {name} counter")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in sorted(_gauges.items()):
            lines.append(f"# HELP {name} gauge")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"
