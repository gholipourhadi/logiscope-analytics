"""Data-quality profiling for accepted shipment datasets."""

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class QualityReport:
    rows: int
    columns: int
    duplicate_shipments: int
    missing_cells: int
    same_city_shipments: int
    date_start: str
    date_end: str
    freshness_days: int
    quality_score: float

    def to_dict(self) -> dict:
        return asdict(self)


def profile_quality(
    frame: pd.DataFrame, as_of: pd.Timestamp | None = None
) -> QualityReport:
    if frame.empty:
        raise ValueError("Cannot profile an empty dataset")
    latest = frame["order_date"].max().normalize()
    reference = (as_of or latest).normalize()
    freshness = max(0, int((reference - latest).days))
    duplicates = int(frame["shipment_id"].duplicated().sum())
    missing = int(frame.isna().sum().sum())
    same_city = int(
        (frame["origin"].str.casefold() == frame["destination"].str.casefold()).sum()
    )
    penalty = min(100.0, duplicates * 5 + missing * 2 + same_city * 2 + freshness * 0.1)
    return QualityReport(
        rows=len(frame),
        columns=len(frame.columns),
        duplicate_shipments=duplicates,
        missing_cells=missing,
        same_city_shipments=same_city,
        date_start=frame["order_date"].min().date().isoformat(),
        date_end=latest.date().isoformat(),
        freshness_days=freshness,
        quality_score=round(max(0.0, 100.0 - penalty), 1),
    )
