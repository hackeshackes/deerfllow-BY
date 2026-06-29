"""Model router — pick the best model for a request.

In v1.5.8 the router is configuration-driven (no ML); the admin sets a
strategy and a set of model costs / quality scores, and the router
returns the appropriate model id. Strategies:

- `COST`    — pick the cheapest model (lowest input cost)
- `QUALITY` — pick the model with the highest quality score
- `SPEED`   — pick the lowest-latency model (lowest p99 — assumed equal
              to `input_per_1k` for the MVP; real implementation will
              read from a latency table)

A new strategy can be added by extending `RoutingStrategy` and the
`_pick_*` mapping below.
"""
from __future__ import annotations

from enum import Enum
from typing import Mapping

from .cost_calculator import ModelCost


class RoutingStrategy(str, Enum):
    COST = "cost"
    QUALITY = "quality"
    SPEED = "speed"


class ModelRouter:
    def __init__(
        self,
        strategy: RoutingStrategy,
        costs: Mapping[str, ModelCost],
        quality_map: Mapping[str, float] | None = None,
    ) -> None:
        if not costs:
            raise ValueError("costs mapping must not be empty")
        if strategy not in RoutingStrategy:
            raise ValueError(f"unknown strategy: {strategy!r}")
        self._strategy = strategy
        self._costs = dict(costs)
        self._quality_map = dict(quality_map or {})

    def pick(self) -> str:
        if self._strategy == RoutingStrategy.COST:
            return min(
                self._costs.keys(),
                key=lambda name: self._costs[name].input_per_1k,
            )
        if self._strategy == RoutingStrategy.QUALITY:
            if not self._quality_map:
                raise ValueError(
                    "quality strategy requires a non-empty quality_map"
                )
            return max(
                self._quality_map.keys(),
                key=lambda name: self._quality_map[name],
            )
        if self._strategy == RoutingStrategy.SPEED:
            # For the MVP, "speed" maps to lowest input cost as a proxy
            # for token-throughput; real implementation will track p99.
            return min(
                self._costs.keys(),
                key=lambda name: self._costs[name].input_per_1k,
            )
        raise ValueError(f"unknown strategy: {self._strategy!r}")
