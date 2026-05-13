from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_and_kpis_endpoints(shipments):
    client = TestClient(create_app())
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert int(health.json()["dataset_rows"]) == len(shipments)
    response = client.get("/api/v1/kpis")
    assert response.status_code == 200
    assert response.json()["shipments"] == len(shipments)


def test_scorecard_and_quality_endpoints():
    client = TestClient(create_app())
    assert client.get("/api/v1/carriers").status_code == 200
    assert client.get("/api/v1/routes?minimum_shipments=10").status_code == 200
    assert client.get("/api/v1/quality").json()["missing_cells"] == 0


def test_forecast_and_anomaly_endpoints():
    client = TestClient(create_app())
    forecast = client.get("/api/v1/forecast?horizon=7")
    assert forecast.status_code == 200
    assert len(forecast.json()["points"]) == 7
    anomalies = client.get("/api/v1/anomalies?contamination=0.03")
    assert anomalies.status_code == 200
    assert anomalies.json()


def test_scenario_endpoint():
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/scenarios",
        json={
            "volume_change_percent": 20,
            "fuel_surcharge_percent": 5,
            "transit_improvement_days": 1,
            "daily_capacity": 20,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["projected_shipments"] > payload["baseline_shipments"]


def test_api_validation_rejects_bad_parameters():
    client = TestClient(create_app())
    assert client.get("/api/v1/forecast?horizon=0").status_code == 422
    assert client.get("/api/v1/routes?minimum_shipments=0").status_code == 422
    assert (
        client.post("/api/v1/scenarios", json={"daily_capacity": 0}).status_code == 422
    )


def test_missing_dataset_returns_domain_error(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "missing.csv"))
    response = client.get("/api/v1/health")
    assert response.status_code == 422
    assert "Unable to read" in response.json()["detail"]
