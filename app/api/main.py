"""FastAPI application factory for machine-readable analytics."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from app.api.schemas import ForecastResponse, ScenarioRequest
from app.core.exceptions import LogiScopeError
from app.services.anomalies import detect_anomalies
from app.services.forecasting import forecast_daily_volume
from app.services.ingestion import load_shipments
from app.services.metrics import calculate_kpis, carrier_scorecard, route_scorecard
from app.services.quality import profile_quality
from app.services.scenarios import ScenarioInput, simulate_scenario

DEFAULT_DATASET = Path(__file__).parents[2] / "data" / "sample_shipments.csv"


def create_app(dataset_path: Path | str = DEFAULT_DATASET) -> FastAPI:
    app = FastAPI(
        title="LogiScope Analytics API",
        version="2.0.0",
        description="Validated logistics KPIs, scorecards, anomalies, and forecasts",
    )
    app.state.dataset_path = Path(dataset_path)

    def dataset():
        try:
            return load_shipments(app.state.dataset_path)
        except LogiScopeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/health")
    def health() -> dict[str, str | int]:
        frame = dataset()
        return {
            "status": "ok",
            "service": app.title,
            "dataset_rows": len(frame),
        }

    @app.get("/api/v1/kpis")
    def kpis() -> dict:
        return calculate_kpis(dataset()).to_dict()

    @app.get("/api/v1/quality")
    def quality() -> dict:
        return profile_quality(dataset()).to_dict()

    @app.get("/api/v1/carriers")
    def carriers() -> list[dict]:
        return carrier_scorecard(dataset()).to_dict(orient="records")

    @app.get("/api/v1/routes")
    def routes(minimum_shipments: int = Query(default=1, ge=1)) -> list[dict]:
        return route_scorecard(dataset(), minimum_shipments).to_dict(orient="records")

    @app.get("/api/v1/anomalies")
    def anomalies(
        contamination: float = Query(default=0.05, gt=0, le=0.25),
    ) -> list[dict]:
        try:
            result = detect_anomalies(dataset(), contamination)
        except (LogiScopeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        columns = [
            "shipment_id",
            "carrier",
            "route",
            "shipping_cost",
            "actual_days",
            "anomaly_score",
            "anomaly_reason",
        ]
        return result.loc[result["anomaly"], columns].to_dict(orient="records")

    @app.get("/api/v1/forecast", response_model=ForecastResponse)
    def forecast(horizon: int = Query(default=14, ge=1, le=90)) -> dict:
        try:
            result = forecast_daily_volume(dataset(), horizon)
        except (LogiScopeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        points = result.forecast.copy()
        points["date"] = points["date"].dt.date.astype(str)
        return {
            "metrics": result.metrics.to_dict(),
            "points": points.to_dict(orient="records"),
        }

    @app.post("/api/v1/scenarios")
    def scenario(request: ScenarioRequest) -> dict:
        inputs = ScenarioInput(**request.model_dump())
        try:
            return simulate_scenario(dataset(), inputs).to_dict()
        except (LogiScopeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()
