"""Capacity and cost what-if simulations."""

from dataclasses import asdict, dataclass

import pandas as pd

from app.core.exceptions import InvalidScenarioError
from app.services.metrics import calculate_kpis


@dataclass(frozen=True, slots=True)
class ScenarioInput:
    volume_change_percent: float = 0.0
    fuel_surcharge_percent: float = 0.0
    transit_improvement_days: float = 0.0
    daily_capacity: int = 100


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    baseline_shipments: int
    projected_shipments: int
    baseline_cost: float
    projected_cost: float
    incremental_cost: float
    baseline_on_time_rate: float
    projected_on_time_rate: float
    peak_daily_demand: int
    required_daily_capacity: int
    capacity_gap: int

    def to_dict(self) -> dict:
        return asdict(self)


def simulate_scenario(frame: pd.DataFrame, inputs: ScenarioInput) -> ScenarioResult:
    _validate(inputs)
    baseline = calculate_kpis(frame)
    volume_factor = 1 + inputs.volume_change_percent / 100
    cost_factor = 1 + inputs.fuel_surcharge_percent / 100
    projected_shipments = round(baseline.shipments * volume_factor)
    projected_cost = baseline.total_cost * volume_factor * cost_factor

    improved_actual = (frame["actual_days"] - inputs.transit_improvement_days).clip(
        lower=0
    )
    projected_on_time = float((improved_actual <= frame["planned_days"]).mean() * 100)
    daily = frame.set_index("order_date").resample("D").size()
    peak = round(float(daily.max()) * volume_factor)
    return ScenarioResult(
        baseline_shipments=baseline.shipments,
        projected_shipments=projected_shipments,
        baseline_cost=baseline.total_cost,
        projected_cost=round(projected_cost, 2),
        incremental_cost=round(projected_cost - baseline.total_cost, 2),
        baseline_on_time_rate=baseline.on_time_rate,
        projected_on_time_rate=round(projected_on_time, 2),
        peak_daily_demand=peak,
        required_daily_capacity=max(inputs.daily_capacity, peak),
        capacity_gap=max(0, peak - inputs.daily_capacity),
    )


def _validate(inputs: ScenarioInput) -> None:
    if not -90 <= inputs.volume_change_percent <= 500:
        raise InvalidScenarioError("volume_change_percent must be between -90 and 500")
    if not -50 <= inputs.fuel_surcharge_percent <= 200:
        raise InvalidScenarioError("fuel_surcharge_percent must be between -50 and 200")
    if not 0 <= inputs.transit_improvement_days <= 30:
        raise InvalidScenarioError("transit_improvement_days must be between 0 and 30")
    if inputs.daily_capacity < 1:
        raise InvalidScenarioError("daily_capacity must be positive")
