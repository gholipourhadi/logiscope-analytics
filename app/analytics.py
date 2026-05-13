"""Backward-compatible facade over the separated analytics services."""

import pandas as pd

from app.services.anomalies import detect_anomalies
from app.services.forecasting import forecast_daily_volume as build_forecast
from app.services.ingestion import load_shipments
from app.services.metrics import calculate_kpis, carrier_scorecard, route_scorecard
from app.services.quality import profile_quality
from app.services.scenarios import ScenarioInput, simulate_scenario


def kpis(frame: pd.DataFrame) -> dict[str, float | int]:
    return calculate_kpis(frame).to_dict()


def forecast_daily_volume(
    frame: pd.DataFrame, horizon: int = 14
) -> tuple[pd.DataFrame, float]:
    result = build_forecast(frame, horizon)
    return result.forecast, result.metrics.mae


__all__ = [
    "ScenarioInput",
    "carrier_scorecard",
    "detect_anomalies",
    "forecast_daily_volume",
    "kpis",
    "load_shipments",
    "profile_quality",
    "route_scorecard",
    "simulate_scenario",
]
