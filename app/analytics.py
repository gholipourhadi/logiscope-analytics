from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error

REQUIRED_COLUMNS = {
    "shipment_id", "order_date", "origin", "destination", "carrier",
    "distance_km", "weight_kg", "shipping_cost", "planned_days",
    "actual_days", "status",
}


def load_shipments(source: str | object) -> pd.DataFrame:
    df = pd.read_csv(source)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    numeric = ["distance_km", "weight_kg", "shipping_cost", "planned_days", "actual_days"]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
    if df["order_date"].isna().any() or df[numeric].isna().any().any():
        raise ValueError("Dataset contains invalid dates or numeric values")
    df["delay_days"] = (df["actual_days"] - df["planned_days"]).clip(lower=0)
    df["on_time"] = df["actual_days"] <= df["planned_days"]
    df["cost_per_km"] = df["shipping_cost"] / df["distance_km"].replace(0, np.nan)
    return df


def kpis(df: pd.DataFrame) -> dict[str, float]:
    return {
        "shipments": int(len(df)),
        "on_time_rate": float(df["on_time"].mean() * 100),
        "total_cost": float(df["shipping_cost"].sum()),
        "avg_delay": float(df["delay_days"].mean()),
        "avg_cost_per_km": float(df["cost_per_km"].mean()),
    }


def carrier_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("carrier", as_index=False)
            .agg(shipments=("shipment_id", "count"),
                 on_time_rate=("on_time", "mean"),
                 avg_delay=("delay_days", "mean"),
                 total_cost=("shipping_cost", "sum"),
                 cost_per_km=("cost_per_km", "mean"))
            .assign(on_time_rate=lambda x: x.on_time_rate * 100)
            .sort_values(["on_time_rate", "cost_per_km"], ascending=[False, True]))


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    features = df[["distance_km", "weight_kg", "shipping_cost", "actual_days"]]
    model = IsolationForest(contamination=contamination, random_state=42)
    result = df.copy()
    result["anomaly"] = model.fit_predict(features) == -1
    result["anomaly_score"] = -model.score_samples(features)
    return result.sort_values("anomaly_score", ascending=False)


def forecast_daily_volume(df: pd.DataFrame, horizon: int = 14) -> tuple[pd.DataFrame, float]:
    daily = df.set_index("order_date").resample("D").size().rename("volume").to_frame()
    daily["day_index"] = np.arange(len(daily))
    daily["weekday"] = daily.index.dayofweek
    daily["rolling_7"] = daily.volume.rolling(7, min_periods=1).mean()
    split = max(7, int(len(daily) * 0.8))
    train, test = daily.iloc[:split], daily.iloc[split:]
    features = ["day_index", "weekday", "rolling_7"]
    model = RandomForestRegressor(n_estimators=250, max_depth=8, random_state=42)
    model.fit(train[features], train.volume)
    mae = float(mean_absolute_error(test.volume, model.predict(test[features]))) if len(test) else 0.0
    future_dates = pd.date_range(daily.index.max() + pd.Timedelta(days=1), periods=horizon)
    future = pd.DataFrame(index=future_dates)
    future["day_index"] = np.arange(len(daily), len(daily) + horizon)
    future["weekday"] = future.index.dayofweek
    future["rolling_7"] = daily.volume.tail(7).mean()
    future["forecast"] = np.maximum(0, model.predict(future[features])).round()
    return future.reset_index(names="date"), mae

