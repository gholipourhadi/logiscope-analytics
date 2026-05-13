"""Demand forecasting with chronological backtesting and intervals."""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

from app.core.exceptions import InsufficientDataError


@dataclass(frozen=True, slots=True)
class ForecastMetrics:
    mae: float
    mape: float
    training_days: int
    validation_days: int
    horizon_days: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ForecastResult:
    forecast: pd.DataFrame
    metrics: ForecastMetrics


def daily_volume(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise InsufficientDataError("Cannot aggregate an empty shipment dataset")
    series = (
        frame.set_index("order_date")
        .resample("D")
        .size()
        .rename("volume")
        .astype(float)
    )
    return _build_features(series)


def forecast_daily_volume(
    frame: pd.DataFrame,
    horizon: int = 14,
    minimum_history_days: int = 28,
) -> ForecastResult:
    if not 1 <= horizon <= 90:
        raise ValueError("horizon must be between 1 and 90 days")
    history = daily_volume(frame)
    if len(history) < minimum_history_days:
        raise InsufficientDataError(
            f"Forecasting requires at least {minimum_history_days} calendar days"
        )

    features = [
        "day_index",
        "weekday",
        "month",
        "lag_1",
        "lag_7",
        "rolling_7",
        "rolling_28",
    ]
    usable = history.dropna().copy()
    validation_size = max(7, min(28, int(len(usable) * 0.2)))
    train = usable.iloc[:-validation_size]
    validation = usable.iloc[-validation_size:]
    if len(train) < 14:
        raise InsufficientDataError("Not enough usable lag history for backtesting")

    model = _model()
    model.fit(train[features], train["volume"])
    validation_prediction = np.maximum(0, model.predict(validation[features]))
    residuals = validation["volume"].to_numpy() - validation_prediction
    mae = float(mean_absolute_error(validation["volume"], validation_prediction))
    non_zero = validation["volume"].replace(0, 1)
    mape = float(mean_absolute_percentage_error(non_zero, validation_prediction) * 100)

    model.fit(usable[features], usable["volume"])
    values = history["volume"].tolist()
    dates = []
    predictions = []
    for offset in range(1, horizon + 1):
        date = history.index.max() + pd.Timedelta(days=offset)
        row = _future_feature_row(date, len(history) + offset - 1, values)
        prediction = max(0.0, float(model.predict(pd.DataFrame([row]))[0]))
        values.append(prediction)
        dates.append(date)
        predictions.append(prediction)

    interval = max(1.0, float(np.quantile(np.abs(residuals), 0.9)))
    forecast = pd.DataFrame(
        {
            "date": dates,
            "forecast": np.round(predictions, 1),
            "lower_bound": np.maximum(0, np.round(np.array(predictions) - interval, 1)),
            "upper_bound": np.round(np.array(predictions) + interval, 1),
        }
    )
    metrics = ForecastMetrics(
        mae=round(mae, 3),
        mape=round(mape, 2),
        training_days=len(train),
        validation_days=len(validation),
        horizon_days=horizon,
    )
    return ForecastResult(forecast, metrics)


def _build_features(series: pd.Series) -> pd.DataFrame:
    result = series.to_frame()
    result["day_index"] = np.arange(len(result))
    result["weekday"] = result.index.dayofweek
    result["month"] = result.index.month
    result["lag_1"] = result["volume"].shift(1)
    result["lag_7"] = result["volume"].shift(7)
    result["rolling_7"] = result["volume"].shift(1).rolling(7).mean()
    result["rolling_28"] = result["volume"].shift(1).rolling(28).mean()
    return result


def _future_feature_row(date: pd.Timestamp, index: int, values: list[float]) -> dict:
    return {
        "day_index": index,
        "weekday": date.dayofweek,
        "month": date.month,
        "lag_1": values[-1],
        "lag_7": values[-7],
        "rolling_7": float(np.mean(values[-7:])),
        "rolling_28": float(np.mean(values[-28:])),
    }


def _model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=350,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
