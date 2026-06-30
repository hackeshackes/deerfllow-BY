"""Tests for the ModelRouter and the cost calculator."""
from __future__ import annotations

import pytest

from app.gateway.multitenancy.cost_calculator import ModelCost, cost_for
from app.gateway.multitenancy.router_service import ModelRouter, RoutingStrategy


# ---------------------------------------------------------------- cost calc
def test_cost_for_returns_dollar_amount():
    cost = ModelCost(name="haiku", input_per_1k=0.001, output_per_1k=0.002)
    # 1000 input + 500 output tokens:
    #   (1000/1000) * 0.001 + (500/1000) * 0.002 = 0.001 + 0.001 = 0.002
    assert cost_for(cost, 1000, 500) == pytest.approx(0.002)


def test_cost_total_method_direct():
    cost = ModelCost(name="sonnet", input_per_1k=0.003, output_per_1k=0.015)
    # 2000 input + 1000 output:
    #   2 * 0.003 + 1 * 0.015 = 0.006 + 0.015 = 0.021
    assert cost.total(2000, 1000) == pytest.approx(0.021)


# ---------------------------------------------------------------- router
def _costs() -> dict[str, ModelCost]:
    return {
        "haiku": ModelCost(name="haiku", input_per_1k=0.001, output_per_1k=0.002),
        "sonnet": ModelCost(name="sonnet", input_per_1k=0.003, output_per_1k=0.015),
        "opus": ModelCost(name="opus", input_per_1k=0.015, output_per_1k=0.075),
    }


def test_cost_strategy_picks_cheapest():
    router = ModelRouter(strategy=RoutingStrategy.COST, costs=_costs())
    assert router.pick() == "haiku"


def test_quality_strategy_picks_highest_score():
    router = ModelRouter(
        strategy=RoutingStrategy.QUALITY,
        costs=_costs(),
        quality_map={"haiku": 0.7, "sonnet": 0.9, "opus": 0.95},
    )
    assert router.pick() == "opus"


def test_speed_strategy_uses_cost_as_proxy():
    """Until latency tracking is wired in, SPEED is a stand-in for COST."""
    router = ModelRouter(strategy=RoutingStrategy.SPEED, costs=_costs())
    assert router.pick() == "haiku"


def test_quality_strategy_requires_quality_map():
    router = ModelRouter(strategy=RoutingStrategy.QUALITY, costs=_costs())
    with pytest.raises(ValueError, match="quality_map"):
        router.pick()


def test_empty_costs_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        ModelRouter(strategy=RoutingStrategy.COST, costs={})


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="unknown strategy"):
        ModelRouter(
            strategy="garbage",  # type: ignore[arg-type]
            costs=_costs(),
        )
