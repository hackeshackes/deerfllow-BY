import pytest
from app.gateway.identity.audit.models import AuditEvent, ActorType


def test_audit_event_creation():
    e = AuditEvent(
        id="evt-1",
        actor_id="u-1",
        actor_type=ActorType.USER,
        action="thread.create",
        resource_type="thread",
        resource_id="t-1",
    )
    assert e.action == "thread.create"
    assert e.success is True  # default


def test_audit_event_with_metadata():
    e = AuditEvent(
        id="evt-1", actor_id="u-1", actor_type=ActorType.USER,
        action="thread.create", resource_type="thread",
        metadata={"key": "value"},
    )
    assert e.metadata == {"key": "value"}


def test_actor_type_enum():
    assert ActorType.USER.value == "user"
    assert ActorType.SYSTEM.value == "system"
    assert ActorType.AUTOMATION.value == "automation"
    assert ActorType.CHANNEL.value == "channel"