"""Deterministic operational KPIs and scorecards."""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class KPIReport:
    shipments: int
    on_time_rate: float
    total_cost: float
    average_cost: float
    average_delay: float
    p95_delay: float
    average_cost_per_km: float
    delayed_shipments: int

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_kpis(frame: pd.DataFrame) -> KPIReport:
    if frame.empty:
        return KPIReport(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
    return KPIReport(
        shipments=len(frame),
        on_time_rate=round(float(frame["on_time"].mean() * 100), 2),
        total_cost=round(float(frame["shipping_cost"].sum()), 2),
        average_cost=round(float(frame["shipping_cost"].mean()), 2),
        average_delay=round(float(frame["delay_days"].mean()), 2),
        p95_delay=round(float(frame["delay_days"].quantile(0.95)), 2),
        average_cost_per_km=round(float(frame["cost_per_km"].mean()), 4),
        delayed_shipments=int((~frame["on_time"]).sum()),
    )


def carrier_scorecard(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    scorecard = (
        frame.groupby("carrier", as_index=False)
        .agg(
            shipments=("shipment_id", "count"),
            on_time_rate=("on_time", "mean"),
            average_delay=("delay_days", "mean"),
            p95_delay=("delay_days", lambda values: values.quantile(0.95)),
            total_cost=("shipping_cost", "sum"),
            average_cost=("shipping_cost", "mean"),
            cost_per_km=("cost_per_km", "mean"),
        )
        .assign(on_time_rate=lambda result: result["on_time_rate"] * 100)
    )
    scorecard["reliability_score"] = np.clip(
        scorecard["on_time_rate"] - scorecard["average_delay"] * 8, 0, 100
    )
    scorecard["cost_index"] = (
        scorecard["cost_per_km"] / scorecard["cost_per_km"].median() * 100
    )
    scorecard["composite_score"] = (
        scorecard["reliability_score"] * 0.7
        + np.clip(200 - scorecard["cost_index"], 0, 100) * 0.3
    )
    return scorecard.round(2).sort_values("composite_score", ascending=False)


def route_scorecard(frame: pd.DataFrame, minimum_shipments: int = 1) -> pd.DataFrame:
    if minimum_shipments < 1:
        raise ValueError("minimum_shipments must be positive")
    if frame.empty:
        return pd.DataFrame()
    routes = (
        frame.groupby(["origin", "destination", "route"], as_index=False)
        .agg(
            shipments=("shipment_id", "count"),
            on_time_rate=("on_time", "mean"),
            average_delay=("delay_days", "mean"),
            total_cost=("shipping_cost", "sum"),
            average_cost=("shipping_cost", "mean"),
            average_distance=("distance_km", "mean"),
        )
        .query("shipments >= @minimum_shipments")
    )
    routes["on_time_rate"] *= 100
    routes["cost_per_shipment"] = routes["total_cost"] / routes["shipments"]
    return routes.round(2).sort_values(
        ["shipments", "total_cost"], ascending=[False, False]
    )
