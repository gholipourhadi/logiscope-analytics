"""Shipment ingestion, normalization, and strict dataset validation."""

from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd

from app.core.exceptions import DatasetValidationError
from app.domain.schema import (
    DEFAULT_POLICY,
    NUMERIC_COLUMNS,
    SHIPMENT_COLUMNS,
    TEXT_COLUMNS,
    ValidationPolicy,
)

DataSource = str | Path | IO[str] | IO[bytes]


def load_shipments(
    source: DataSource, policy: ValidationPolicy = DEFAULT_POLICY
) -> pd.DataFrame:
    """Load a CSV, enforce the canonical contract, and derive stable features."""

    try:
        raw = pd.read_csv(source)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DatasetValidationError(f"Unable to read shipment CSV: {exc}") from exc
    return normalize_shipments(raw, policy)


def normalize_shipments(
    raw: pd.DataFrame, policy: ValidationPolicy = DEFAULT_POLICY
) -> pd.DataFrame:
    if raw.empty:
        raise DatasetValidationError("Dataset must contain at least one shipment")
    if len(raw) > policy.maximum_rows:
        raise DatasetValidationError(
            f"Dataset exceeds the {policy.maximum_rows:,}-row safety limit"
        )

    missing = sorted(set(SHIPMENT_COLUMNS) - set(raw.columns))
    if missing:
        raise DatasetValidationError(f"Missing required columns: {', '.join(missing)}")

    frame = raw.loc[:, SHIPMENT_COLUMNS].copy()
    frame["order_date"] = pd.to_datetime(
        frame["order_date"], errors="coerce", format="mixed"
    )
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in TEXT_COLUMNS:
        frame[column] = frame[column].astype("string").str.strip()

    _validate_nulls(frame)
    _validate_business_rules(frame, policy)

    frame["delay_days"] = (frame["actual_days"] - frame["planned_days"]).clip(lower=0)
    frame["on_time"] = frame["actual_days"] <= frame["planned_days"]
    frame["cost_per_km"] = frame["shipping_cost"] / frame["distance_km"]
    frame["cost_per_kg"] = frame["shipping_cost"] / frame["weight_kg"]
    frame["route"] = frame["origin"] + " → " + frame["destination"]
    frame["order_month"] = frame["order_date"].dt.to_period("M").astype(str)
    frame["weekday"] = frame["order_date"].dt.day_name()
    return frame.sort_values(["order_date", "shipment_id"]).reset_index(drop=True)


def _validate_nulls(frame: pd.DataFrame) -> None:
    invalid = [column for column in frame.columns if frame[column].isna().any()]
    empty_text = [
        column for column in TEXT_COLUMNS if frame[column].fillna("").eq("").any()
    ]
    problems = sorted(set(invalid + empty_text))
    if problems:
        raise DatasetValidationError(
            f"Dataset contains null, invalid, or empty values in: {', '.join(problems)}"
        )


def _validate_business_rules(frame: pd.DataFrame, policy: ValidationPolicy) -> None:
    if not policy.allow_duplicate_ids and frame["shipment_id"].duplicated().any():
        duplicate = frame.loc[frame["shipment_id"].duplicated(), "shipment_id"].iloc[0]
        raise DatasetValidationError(f"Duplicate shipment_id detected: {duplicate}")
    if (frame["distance_km"] < policy.minimum_distance_km).any():
        raise DatasetValidationError("distance_km must be greater than zero")
    if (frame["weight_kg"] < policy.minimum_weight_kg).any():
        raise DatasetValidationError("weight_kg must be greater than zero")
    if (frame["shipping_cost"] < policy.minimum_shipping_cost).any():
        raise DatasetValidationError("shipping_cost cannot be negative")
    transit = frame[["planned_days", "actual_days"]]
    if (transit < 0).any().any():
        raise DatasetValidationError("Transit days cannot be negative")
    if (transit > policy.maximum_transit_days).any().any():
        raise DatasetValidationError(
            f"Transit days cannot exceed {policy.maximum_transit_days}"
        )
    if not policy.allow_same_origin_destination:
        same = frame["origin"].str.casefold() == frame["destination"].str.casefold()
        if same.any():
            raise DatasetValidationError(
                "Origin and destination must differ for every shipment"
            )
    if not np.isfinite(frame[list(NUMERIC_COLUMNS)].to_numpy()).all():
        raise DatasetValidationError("Numeric fields must contain finite values")
