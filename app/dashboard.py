"""Interactive operations dashboard for LogiScope Analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.core.exceptions import LogiScopeError
from app.services.anomalies import detect_anomalies
from app.services.forecasting import forecast_daily_volume
from app.services.ingestion import load_shipments
from app.services.metrics import calculate_kpis, carrier_scorecard, route_scorecard
from app.services.quality import profile_quality
from app.services.scenarios import ScenarioInput, simulate_scenario

DATASET = Path(__file__).parents[1] / "data" / "sample_shipments.csv"


@st.cache_data(show_spinner=False)
def read_dataset(source: object) -> pd.DataFrame:
    """Load and validate a shipment dataset while preserving Streamlit caching."""
    return load_shipments(source)


def apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return the selected dataset slice."""
    st.sidebar.header("Filters")
    options = sorted(frame["carrier"].unique())
    carriers = st.sidebar.multiselect("Carrier", options, default=options)
    selected_dates = st.sidebar.date_input(
        "Order date",
        value=(frame["order_date"].min(), frame["order_date"].max()),
    )
    filtered = frame[frame["carrier"].isin(carriers)]
    if len(selected_dates) == 2:
        start, end = map(pd.Timestamp, selected_dates)
        filtered = filtered[filtered["order_date"].between(start, end)]
    return filtered


def render_metrics(frame: pd.DataFrame) -> None:
    report = calculate_kpis(frame)
    values = (
        ("Shipments", f"{report.shipments:,}"),
        ("On-time rate", f"{report.on_time_rate:.1f}%"),
        ("Total cost", f"€{report.total_cost:,.0f}"),
        ("Average delay", f"{report.average_delay:.2f} d"),
        ("Cost / km", f"€{report.average_cost_per_km:.2f}"),
    )
    for column, (label, value) in zip(st.columns(5), values, strict=True):
        column.metric(label, value)


def render_overview(frame: pd.DataFrame) -> None:
    left, right = st.columns(2)
    daily = (
        frame.set_index("order_date")
        .resample("D")
        .size()
        .rename("shipments")
        .reset_index()
    )
    left.plotly_chart(
        px.area(daily, x="order_date", y="shipments", title="Daily shipment volume"),
        use_container_width=True,
    )
    routes = route_scorecard(frame).head(12)
    right.plotly_chart(
        px.bar(
            routes,
            x="total_cost",
            y="route",
            color="on_time_rate",
            orientation="h",
            title="Highest-cost routes",
            color_continuous_scale="Tealgrn",
        ),
        use_container_width=True,
    )


def render_carriers(frame: pd.DataFrame) -> None:
    scores = carrier_scorecard(frame)
    st.plotly_chart(
        px.scatter(
            scores,
            x="cost_per_km",
            y="on_time_rate",
            size="shipments",
            color="composite_score",
            hover_name="carrier",
            title="Carrier cost, reliability and composite score",
            color_continuous_scale="Viridis",
        ),
        use_container_width=True,
    )
    st.dataframe(scores, use_container_width=True, hide_index=True)


def render_forecast(frame: pd.DataFrame) -> None:
    horizon = st.slider("Forecast horizon", 7, 30, 14)
    result = forecast_daily_volume(frame, horizon=horizon)
    st.metric("Backtest MAE", f"{result.metrics.mae:.2f} shipments/day")
    st.caption(
        f"Chronological holdout: {result.metrics.validation_days} days · "
        f"MAPE {result.metrics.mape:.1f}%"
    )
    chart = result.forecast.melt(
        id_vars="date",
        value_vars=["lower_bound", "forecast", "upper_bound"],
        var_name="series",
        value_name="shipments",
    )
    st.plotly_chart(
        px.line(chart, x="date", y="shipments", color="series", markers=True),
        use_container_width=True,
    )


def render_anomalies(frame: pd.DataFrame) -> None:
    contamination = st.slider("Expected anomaly rate", 0.01, 0.15, 0.04, 0.01)
    scored = detect_anomalies(frame, contamination=contamination)
    flagged = scored[scored["anomaly"]].sort_values("anomaly_score", ascending=False)
    st.metric("Flagged shipments", len(flagged))
    columns = [
        "shipment_id",
        "carrier",
        "route",
        "shipping_cost",
        "actual_days",
        "anomaly_score",
        "anomaly_reason",
    ]
    st.dataframe(flagged[columns], use_container_width=True, hide_index=True)


def render_scenario(frame: pd.DataFrame) -> None:
    st.subheader("Operational scenario simulator")
    left, middle, right = st.columns(3)
    volume = left.slider("Volume change", -30, 100, 20) / 100
    fuel = middle.slider("Fuel cost change", -30, 100, 10) / 100
    capacity = right.number_input("Daily capacity", min_value=1, value=12)
    transit = st.slider("Transit-time change", -30, 100, 0) / 100
    result = simulate_scenario(
        frame,
        ScenarioInput(
            volume_change_percent=volume * 100,
            fuel_surcharge_percent=fuel * 100,
            transit_improvement_days=max(0, -transit * 3),
            daily_capacity=int(capacity),
        ),
    )
    values = (
        ("Projected shipments", f"{result.projected_shipments:,}"),
        ("Projected cost", f"€{result.projected_cost:,.0f}"),
        ("Incremental cost", f"€{result.incremental_cost:,.0f}"),
        ("Capacity gap", f"{result.capacity_gap:,}"),
    )
    for column, (label, value) in zip(st.columns(4), values, strict=True):
        column.metric(label, value)


def main() -> None:
    st.set_page_config(page_title="LogiScope Analytics", page_icon="📦", layout="wide")
    st.title("📦 LogiScope Analytics")
    st.caption(
        "Validated shipment intelligence, forecasting and operational simulation"
    )

    uploaded = st.sidebar.file_uploader("Upload shipment CSV", type="csv")
    try:
        frame = read_dataset(uploaded or DATASET)
        filtered = apply_filters(frame)
        if filtered.empty:
            st.warning("No shipments match the selected filters.")
            st.stop()
        render_metrics(filtered)
        tabs = st.tabs(
            [
                "Overview",
                "Carriers",
                "Forecast",
                "Anomalies",
                "Scenario",
                "Quality",
                "Data",
            ]
        )
        with tabs[0]:
            render_overview(filtered)
        with tabs[1]:
            render_carriers(filtered)
        with tabs[2]:
            render_forecast(filtered)
        with tabs[3]:
            render_anomalies(filtered)
        with tabs[4]:
            render_scenario(filtered)
        with tabs[5]:
            st.json(profile_quality(filtered).as_dict())
        with tabs[6]:
            st.dataframe(filtered, use_container_width=True, height=480)
            st.download_button(
                "Download filtered CSV",
                filtered.to_csv(index=False),
                "logiscope_filtered.csv",
                "text/csv",
            )
    except (LogiScopeError, ValueError) as exc:
        st.error(str(exc))
        st.stop()


if __name__ == "__main__":
    main()
