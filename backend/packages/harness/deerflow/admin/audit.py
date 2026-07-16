from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from deerflow.config.paths import get_paths


def append_admin_audit_record(action: str, *, actor_id: str | None, target: str, details: dict[str, Any] | None = None) -> None:
    path = get_paths().admin_audit_file
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "actor_id": actor_id,
        "target": target,
        "details": details or {},
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def read_admin_audit_records(limit: int = 200) -> list[dict[str, Any]]:
    path = get_paths().admin_audit_file
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return list(reversed(records[-limit:]))


def filter_admin_audit_records(
    records: list[dict[str, Any]],
    *,
    action_prefix: str | None = None,
    actor_id: str | None = None,
) -> list[dict[str, Any]]:
    """In-memory filter for the small per-process audit log.

    The admin audit log is a single JSONL file, so we read the tail and
    filter in-process. Keep the predicate pure so tests can call it
    without touching the filesystem.
    """
    out: list[dict[str, Any]] = []
    for r in records:
        if action_prefix and not r.get("action", "").startswith(action_prefix):
            continue
        if actor_id and r.get("actor_id") != actor_id:
            continue
        out.append(r)
    return out
