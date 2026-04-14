from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from deerflow.config.paths import get_paths


def _metadata_path():
    return get_paths().admin_skill_metadata_file


def read_skill_metadata() -> dict[str, dict[str, Any]]:
    path = _metadata_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def write_skill_metadata(data: dict[str, dict[str, Any]]) -> None:
    path = _metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


def upsert_skill_metadata(skill_name: str, **metadata: Any) -> dict[str, Any]:
    payload = read_skill_metadata()
    existing = payload.get(skill_name, {})
    record = {
        **existing,
        **metadata,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    payload[skill_name] = record
    write_skill_metadata(payload)
    return record
