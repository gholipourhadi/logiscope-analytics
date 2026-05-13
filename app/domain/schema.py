"""Canonical shipment schema and validation configuration."""

from dataclasses import dataclass

SHIPMENT_COLUMNS = (
    "shipment_id",
    "order_date",
    "origin",
    "destination",
    "carrier",
    "distance_km",
    "weight_kg",
    "shipping_cost",
    "planned_days",
    "actual_days",
    "status",
)

NUMERIC_COLUMNS = (
    "distance_km",
    "weight_kg",
    "shipping_cost",
    "planned_days",
    "actual_days",
)

TEXT_COLUMNS = ("shipment_id", "origin", "destination", "carrier", "status")


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    allow_duplicate_ids: bool = False
    # Same-city shipments are valid for urban and last-mile operations. Teams
    # that only operate inter-city lanes can opt into stricter validation.
    allow_same_origin_destination: bool = True
    maximum_rows: int = 1_000_000
    minimum_distance_km: float = 0.01
    minimum_weight_kg: float = 0.01
    minimum_shipping_cost: float = 0.0
    maximum_transit_days: int = 365


DEFAULT_POLICY = ValidationPolicy()
