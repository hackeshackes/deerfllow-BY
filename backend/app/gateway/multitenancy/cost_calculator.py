"""Per-model cost data and cost calculation.

Cost values are USD per 1K tokens. The cost calculator converts token
counts to a USD amount given a model's `input_per_1k` and `output_per_1k`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCost:
    name: str
    input_per_1k: float
    output_per_1k: float

    def total(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1000.0) * self.input_per_1k
            + (output_tokens / 1000.0) * self.output_per_1k
        )


def cost_for(cost: ModelCost, input_tokens: int, output_tokens: int) -> float:
    """Return the dollar cost of one inference at the given token counts."""
    return cost.total(input_tokens, output_tokens)
