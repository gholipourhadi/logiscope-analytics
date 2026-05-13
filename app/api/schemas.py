"""Validated API contracts."""

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    volume_change_percent: float = Field(default=0, ge=-90, le=500)
    fuel_surcharge_percent: float = Field(default=0, ge=-50, le=200)
    transit_improvement_days: float = Field(default=0, ge=0, le=30)
    daily_capacity: int = Field(default=100, ge=1, le=1_000_000)


class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    metrics: dict[str, float | int]
    points: list[ForecastPoint]
