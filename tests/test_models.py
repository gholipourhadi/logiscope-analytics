import pandas as pd
import pytest

from app.core.exceptions import InsufficientDataError, InvalidScenarioError
from app.services.anomalies import detect_anomalies
from app.services.forecasting import forecast_daily_volume
from app.services.scenarios import ScenarioInput, simulate_scenario


def test_anomalies_are_ranked_and_explained(shipments):
    result = detect_anomalies(shipments, contamination=0.04)
    flagged = result[result["anomaly"]]
    assert 80 <= len(flagged) <= 120
    assert flagged["anomaly_score"].notna().all()
    assert flagged["anomaly_reason"].ne("not_flagged").all()


@pytest.mark.parametrize("contamination", [0, -0.1, 0.3])
def test_anomaly_detector_rejects_invalid_contamination(shipments, contamination):
    with pytest.raises(ValueError, match="contamination"):
        detect_anomalies(shipments, contamination)


def test_anomaly_detector_requires_enough_rows(shipments):
    with pytest.raises(InsufficientDataError, match="at least"):
        detect_anomalies(shipments.head(10))


def test_forecast_has_backtest_metrics_and_bounded_points(shipments):
    result = forecast_daily_volume(shipments, horizon=14)
    assert len(result.forecast) == 14
    assert result.metrics.validation_days >= 7
    assert result.metrics.mae >= 0
    assert (result.forecast["lower_bound"] <= result.forecast["forecast"]).all()
    assert (result.forecast["forecast"] <= result.forecast["upper_bound"]).all()


@pytest.mark.parametrize("horizon", [0, 91])
def test_forecast_rejects_invalid_horizon(shipments, horizon):
    with pytest.raises(ValueError, match="horizon"):
        forecast_daily_volume(shipments, horizon)


def test_forecast_rejects_short_history(shipments):
    cutoff = shipments["order_date"].min() + pd.Timedelta(days=20)
    with pytest.raises(InsufficientDataError):
        forecast_daily_volume(shipments[shipments["order_date"] < cutoff])


def test_scenario_projects_cost_and_capacity(shipments):
    result = simulate_scenario(
        shipments,
        ScenarioInput(
            volume_change_percent=25,
            fuel_surcharge_percent=10,
            transit_improvement_days=1,
            daily_capacity=5,
        ),
    )
    assert result.projected_shipments == round(len(shipments) * 1.25)
    assert result.projected_cost > result.baseline_cost
    assert result.projected_on_time_rate >= result.baseline_on_time_rate
    assert result.capacity_gap >= 0


@pytest.mark.parametrize(
    "inputs",
    [
        ScenarioInput(volume_change_percent=-100),
        ScenarioInput(fuel_surcharge_percent=300),
        ScenarioInput(transit_improvement_days=-1),
        ScenarioInput(daily_capacity=0),
    ],
)
def test_scenario_rejects_invalid_assumptions(shipments, inputs):
    with pytest.raises(InvalidScenarioError):
        simulate_scenario(shipments, inputs)
