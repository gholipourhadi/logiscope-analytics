import io

import pandas as pd
import pytest

from app.core.exceptions import DatasetValidationError
from app.domain.schema import ValidationPolicy
from app.generate_data import generate
from app.services.ingestion import load_shipments, normalize_shipments


def test_normalization_derives_operational_features(raw_shipments):
    frame = normalize_shipments(raw_shipments)
    assert frame["delay_days"].tolist() == [0, 2]
    assert frame["on_time"].tolist() == [True, False]
    assert frame["route"].iloc[0] == "Berlin → Munich"
    assert frame["cost_per_km"].gt(0).all()


def test_load_shipments_accepts_file_like_object(raw_shipments):
    stream = io.StringIO(raw_shipments.to_csv(index=False))
    assert len(load_shipments(stream)) == 2


@pytest.mark.parametrize("column", ["shipment_id", "distance_km", "order_date"])
def test_missing_required_column_is_rejected(raw_shipments, column):
    with pytest.raises(DatasetValidationError, match="Missing required columns"):
        normalize_shipments(raw_shipments.drop(columns=column))


def test_duplicate_identifiers_are_rejected(raw_shipments):
    raw_shipments.loc[1, "shipment_id"] = "SHP-1"
    with pytest.raises(DatasetValidationError, match="Duplicate"):
        normalize_shipments(raw_shipments)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("distance_km", 0, "distance_km"),
        ("weight_kg", -2, "weight_kg"),
        ("shipping_cost", -1, "shipping_cost"),
        ("actual_days", -1, "Transit days"),
    ],
)
def test_invalid_numeric_business_rules_are_rejected(
    raw_shipments, column, value, message
):
    raw_shipments.loc[0, column] = value
    with pytest.raises(DatasetValidationError, match=message):
        normalize_shipments(raw_shipments)


def test_invalid_date_is_reported_as_validation_error(raw_shipments):
    raw_shipments.loc[0, "order_date"] = "not-a-date"
    with pytest.raises(DatasetValidationError, match="order_date"):
        normalize_shipments(raw_shipments)


def test_strict_policy_rejects_same_city_lane(raw_shipments):
    raw_shipments.loc[0, "destination"] = "Berlin"
    policy = ValidationPolicy(allow_same_origin_destination=False)
    with pytest.raises(DatasetValidationError, match="must differ"):
        normalize_shipments(raw_shipments, policy)


def test_empty_dataset_is_rejected():
    with pytest.raises(DatasetValidationError, match="at least one"):
        normalize_shipments(pd.DataFrame())


def test_generator_creates_reproducible_valid_data(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    generate(first, rows=50)
    generate(second, rows=50)
    first_frame = load_shipments(first)
    second_frame = load_shipments(second)
    assert len(first_frame) == 50
    assert first_frame.equals(second_frame)
    assert first_frame["origin"].ne(first_frame["destination"]).all()


def test_generator_rejects_nonpositive_row_count(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        generate(tmp_path / "invalid.csv", rows=0)
