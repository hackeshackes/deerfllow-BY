"""Tests for the in-process connector registry."""
from __future__ import annotations

import pytest

from app.gateway.connectors.base import BaseConnector, ConnectorResponse
from app.gateway.connectors.registry import (
    ConnectorRegistry,
    get_registry,
    reset_registry,
)


class FakeConn(BaseConnector):
    name = "fake"

    async def send(self, message):  # type: ignore[override]
        return ConnectorResponse(success=True)

    async def receive_webhook(self, payload):  # type: ignore[override]
        return []


class OtherConn(BaseConnector):
    name = "other"

    async def send(self, message):  # type: ignore[override]
        return ConnectorResponse(success=True)

    async def receive_webhook(self, payload):  # type: ignore[override]
        return []


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure each test gets a fresh global registry."""
    reset_registry()
    yield
    reset_registry()


def test_registry_register_and_get():
    reg = ConnectorRegistry()
    c = FakeConn()
    reg.register(c)
    assert reg.get("fake") is c


def test_registry_get_unknown_raises():
    reg = ConnectorRegistry()
    with pytest.raises(KeyError, match="not registered"):
        reg.get("nonexistent")


def test_registry_list_names():
    reg = ConnectorRegistry()
    reg.register(FakeConn())
    reg.register(OtherConn())
    names = reg.list_names()
    assert set(names) == {"fake", "other"}


def test_registry_unregister():
    reg = ConnectorRegistry()
    reg.register(FakeConn())
    reg.unregister("fake")
    with pytest.raises(KeyError):
        reg.get("fake")


def test_registry_unregister_unknown_is_idempotent():
    """Unregistering a missing name should not raise — used for hot-reload paths."""
    reg = ConnectorRegistry()
    reg.unregister("missing")  # should not raise


def test_registry_register_replaces_existing():
    """Re-registering a connector with the same name should replace the old one."""
    reg = ConnectorRegistry()
    first = FakeConn()
    second = FakeConn()
    reg.register(first)
    reg.register(second)
    assert reg.get("fake") is second
    assert reg.list_names().count("fake") == 1


def test_singleton_get_registry_returns_same_instance():
    a = get_registry()
    b = get_registry()
    assert a is b


def test_singleton_register_then_get():
    reg = get_registry()
    reg.register(FakeConn())
    assert get_registry().get("fake") is not None


def test_singleton_reset_clears_state():
    reg = get_registry()
    reg.register(FakeConn())
    reset_registry()
    assert get_registry().list_names() == []
