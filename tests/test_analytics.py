from app.analytics import carrier_scorecard, detect_anomalies, kpis, load_shipments


def test_sample_data_loads():
    df = load_shipments("data/sample_shipments.csv")
    assert len(df) == 2500
    assert {"delay_days", "on_time", "cost_per_km"}.issubset(df.columns)


def test_kpis_are_valid():
    values = kpis(load_shipments("data/sample_shipments.csv"))
    assert values["shipments"] == 2500
    assert 0 <= values["on_time_rate"] <= 100
    assert values["total_cost"] > 0


def test_models_return_expected_outputs():
    df = load_shipments("data/sample_shipments.csv")
    assert len(carrier_scorecard(df)) == 4
    assert detect_anomalies(df).anomaly.sum() > 0

