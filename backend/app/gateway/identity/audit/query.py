"""Audit event export utilities."""
from __future__ import annotations

import csv
import io
import json

from .models import AuditEvent


def export_events_csv(events: list[AuditEvent]) -> str:
    """Export a list of AuditEvents to CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "occurred_at", "actor_id", "actor_type", "action",
        "resource_type", "resource_id", "workspace_id", "success", "metadata_json",
    ])
    for e in events:
        writer.writerow([
            e.id, e.occurred_at, e.actor_id, e.actor_type.value, e.action,
            e.resource_type, e.resource_id or "", e.workspace_id or "",
            1 if e.success else 0, json.dumps(e.metadata),
        ])
    return buf.getvalue()