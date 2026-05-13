"""Shared deterministic test data."""

from pathlib import Path

import pandas as pd
import pytest

from app.services.ingestion import load_shipments


@pytest.fixture(scope="session")
def shipments() -> pd.DataFrame:
    path = Path(__file__).parents[1] / "data" / "sample_shipments.csv"
    return load_shipments(path)


@pytest.fixture
def raw_shipments() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "shipment_id": ["SHP-1", "SHP-2"],
            "order_date": ["2026-01-01", "2026-01-02"],
            "origin": ["Berlin", "Hamburg"],
            "destination": ["Munich", "Cologne"],
            "carrier": ["DHL", "UPS"],
            "distance_km": [580, 420],
            "weight_kg": [120.5, 82.0],
            "shipping_cost": [315.0, 241.0],
            "planned_days": [2, 2],
            "actual_days": [2, 4],
            "status": ["On time", "Delayed"],
        }
    )
