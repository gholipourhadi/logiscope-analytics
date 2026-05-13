"""Explainable multivariate shipment anomaly detection."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from app.core.exceptions import InsufficientDataError

FEATURES = ("distance_km", "weight_kg", "shipping_cost", "actual_days")


def detect_anomalies(
    frame: pd.DataFrame, contamination: float = 0.05, minimum_rows: int = 20
) -> pd.DataFrame:
    if not 0 < contamination <= 0.25:
        raise ValueError("contamination must be greater than 0 and at most 0.25")
    if len(frame) < minimum_rows:
        raise InsufficientDataError(
            f"Anomaly detection requires at least {minimum_rows} shipments"
        )

    result = frame.copy()
    feature_frame = result.loc[:, FEATURES]
    scaled = RobustScaler().fit_transform(feature_frame)
    model = IsolationForest(
        contamination=contamination,
        n_estimators=300,
        random_state=42,
        n_jobs=1,
    )
    prediction = model.fit_predict(scaled)
    result["anomaly"] = prediction == -1
    result["anomaly_score"] = -model.score_samples(scaled)

    medians = feature_frame.median()
    deviations = (feature_frame - medians).abs()
    mad = deviations.median().replace(0, 1.0)
    robust_z = deviations / mad
    reason_column = robust_z.idxmax(axis=1)
    result["anomaly_reason"] = np.where(
        result["anomaly"], reason_column.map(_REASON_LABELS), "not_flagged"
    )
    return result.sort_values("anomaly_score", ascending=False).reset_index(drop=True)


_REASON_LABELS = {
    "distance_km": "unusual_distance",
    "weight_kg": "unusual_weight",
    "shipping_cost": "unusual_cost",
    "actual_days": "unusual_transit_time",
}
