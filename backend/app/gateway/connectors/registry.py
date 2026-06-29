"""In-process registry of connector instances.

The registry is process-local. It is used by:
- the runtime (`ConnectorRuntime`) to look up a connector by name
- the admin API to list which connectors are loaded
- the YAML loader to register connectors at startup

Thread-safety: a `threading.RLock` guards all mutations and reads so that
concurrent startup / hot-reload paths don't race with message routing.
"""
from __future__ import annotations

from threading import RLock

from .base import BaseConnector


class ConnectorRegistry:
    """A keyed map of `BaseConnector` instances.

    Registering a connector with a name that is already present replaces the
    existing entry — this is intentional so that config reloads can swap a
    connector without first calling `unregister`.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}
        self._lock = RLock()

    def register(self, connector: BaseConnector) -> None:
        if not connector.name:
            raise ValueError("connector.name must be set before registration")
        with self._lock:
            self._connectors[connector.name] = connector

    def unregister(self, name: str) -> None:
        """Remove a connector. Missing names are ignored (idempotent)."""
        with self._lock:
            self._connectors.pop(name, None)

    def get(self, name: str) -> BaseConnector:
        with self._lock:
            try:
                return self._connectors[name]
            except KeyError as e:
                raise KeyError(f"connector {name!r} not registered") from e

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._connectors.keys())

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._connectors

    def __len__(self) -> int:
        with self._lock:
            return len(self._connectors)


_registry: ConnectorRegistry | None = None
_registry_lock = RLock()


def get_registry() -> ConnectorRegistry:
    """Return the process-wide singleton registry."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ConnectorRegistry()
        return _registry


def reset_registry() -> None:
    """Clear the singleton — used by tests to isolate state."""
    global _registry
    with _registry_lock:
        _registry = None
