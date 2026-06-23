"""SIEM exporters. Splunk HEC first; ELK/Syslog in subsequent tasks."""
from __future__ import annotations

import json
from typing import Any

import httpx


class SplunkExporter:
    """Send audit events to Splunk via HTTP Event Collector (HEC)."""

    def __init__(self, hec_url: str, hec_token: str, timeout: float = 5.0):
        self._url = hec_url
        self._token = hec_token
        self._timeout = timeout

    async def export_one(self, event: dict) -> bool:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    self._url,
                    headers={"Authorization": f"Splunk {self._token}"},
                    json={"event": event, "sourcetype": "micx:audit"},
                )
                return resp.status_code == 200
            except httpx.HTTPError:
                return False

    async def export_batch(self, events: list[dict]) -> int:
        """Export a batch; return count successfully sent."""
        count = 0
        for e in events:
            if await self.export_one(e):
                count += 1
        return count