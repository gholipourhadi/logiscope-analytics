import pandas as pd
import pytest

from app.services.metrics import calculate_kpis, carrier_scorecard, route_scorecard
from app.services.quality import profile_quality


def test_kpis_match_underlying_data(shipments):
    report = calculate_kpis(shipments)
    assert report.shipments == len(shipments)
    assert report.total_cost == round(shipments["shipping_cost"].sum(), 2)
    assert 0 <= report.on_time_rate <= 100
    assert report.delayed_shipments == int((~shipments["on_time"]).sum())


def test_empty_kpis_are_well_defined():
    report = calculate_kpis(pd.DataFrame())
    assert report.shipments == 0
    assert report.total_cost == 0


def test_carrier_scorecard_is_ranked(shipments):
    result = carrier_scorecard(shipments)
    assert set(result["carrier"]) == set(shipments["carrier"])
    assert result["composite_score"].is_monotonic_decreasing
    assert result["on_time_rate"].between(0, 100).all()


def test_route_scorecard_respects_minimum_volume(shipments):
    result = route_scorecard(shipments, minimum_shipments=50)
    assert result["shipments"].ge(50).all()


def test_route_scorecard_rejects_nonpositive_threshold(shipments):
    with pytest.raises(ValueError, match="positive"):
        route_scorecard(shipments, 0)


def test_quality_report_tracks_dataset_shape(shipments):
    report = profile_quality(shipments)
    assert report.rows == len(shipments)
    assert report.missing_cells == 0
    assert 0 <= report.quality_score <= 100


def test_quality_report_rejects_empty_dataset():
    with pytest.raises(ValueError, match="empty"):
        profile_quality(pd.DataFrame())
