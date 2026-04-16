from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from deerflow.config.paths import get_paths


class TokenUsageStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path

    @property
    def path(self):
        if self._path:
            return self._path
        return get_paths().admin_dir / "token-usage.jsonl"

    def record(
        self,
        user_id: str,
        thread_id: str | None,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        *,
        run_id: str | None = None,
    ) -> None:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    def get_all(self, since: datetime | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if since is not None:
                ts = datetime.fromisoformat(record["ts"])
                if ts < since:
                    continue
            records.append(record)
        return records[-limit:]

    def get_by_user(self, user_id: str, since: datetime | None = None, limit: int = 500) -> list[dict[str, Any]]:
        return [r for r in self.get_all(since=since, limit=limit * 2) if r.get("user_id") == user_id][-limit:]

    def aggregate_by_user(self, since: datetime | None = None) -> dict[str, dict[str, int]]:
        records = self.get_all(since=since, limit=10000)
        result: dict[str, dict[str, int]] = {}
        for r in records:
            uid = r.get("user_id")
            if uid not in result:
                result[uid] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}
            result[uid]["input_tokens"] += r.get("input_tokens", 0) or 0
            result[uid]["output_tokens"] += r.get("output_tokens", 0) or 0
            result[uid]["total_tokens"] += r.get("total_tokens", 0) or 0
            result[uid]["request_count"] += 1
        return result

    def aggregate_by_model(self, since: datetime | None = None) -> dict[str, dict[str, int]]:
        records = self.get_all(since=since, limit=10000)
        result: dict[str, dict[str, int]] = {}
        for r in records:
            model = r.get("model_name", "unknown")
            if model not in result:
                result[model] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}
            result[model]["input_tokens"] += r.get("input_tokens", 0) or 0
            result[model]["output_tokens"] += r.get("output_tokens", 0) or 0
            result[model]["total_tokens"] += r.get("total_tokens", 0) or 0
            result[model]["request_count"] += 1
        return result

    def total(self, since: datetime | None = None) -> dict[str, int]:
        records = self.get_all(since=since, limit=10000)
        return {
            "input_tokens": sum(r.get("input_tokens", 0) or 0 for r in records),
            "output_tokens": sum(r.get("output_tokens", 0) or 0 for r in records),
            "total_tokens": sum(r.get("total_tokens", 0) or 0 for r in records),
            "request_count": len(records),
        }


_token_usage_store: TokenUsageStore | None = None


def get_token_usage_store() -> TokenUsageStore:
    global _token_usage_store
    if _token_usage_store is None:
        _token_usage_store = TokenUsageStore()
    return _token_usage_store
