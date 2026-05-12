from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.analytics import carrier_scorecard, detect_anomalies, forecast_daily_volume, kpis, load_shipments

st.set_page_config(page_title="LogiScope Analytics", page_icon="📦", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.5rem}.stMetric{background:#111827;border:1px solid #263244;
border-radius:14px;padding:16px}.stApp{background:#07101f;color:#eef2ff}
</style>""", unsafe_allow_html=True)

st.title("📦 LogiScope Analytics")
st.caption("Supply-chain intelligence, carrier performance and predictive operations")

uploaded = st.sidebar.file_uploader("Upload shipment CSV", type="csv")
source = uploaded or Path("data/sample_shipments.csv")
try:
    df = load_shipments(source)
except Exception as exc:
    st.error(str(exc)); st.stop()

st.sidebar.header("Filters")
carriers = st.sidebar.multiselect("Carrier", sorted(df.carrier.unique()), default=sorted(df.carrier.unique()))
date_range = st.sidebar.date_input("Order date", [df.order_date.min(), df.order_date.max()])
filtered = df[df.carrier.isin(carriers)]
if len(date_range) == 2:
    filtered = filtered[filtered.order_date.between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]

metrics = kpis(filtered)
cols = st.columns(5)
labels = [("Shipments", f"{metrics['shipments']:,}"), ("On-time rate", f"{metrics['on_time_rate']:.1f}%"),
          ("Total cost", f"€{metrics['total_cost']:,.0f}"), ("Avg delay", f"{metrics['avg_delay']:.2f} d"),
          ("Cost / km", f"€{metrics['avg_cost_per_km']:.2f}")]
for col, (label, value) in zip(cols, labels): col.metric(label, value)

overview, carriers_tab, forecast_tab, anomalies_tab, data_tab = st.tabs(
    ["Overview", "Carrier scorecard", "Demand forecast", "Anomalies", "Data explorer"])
with overview:
    left, right = st.columns(2)
    daily = filtered.set_index("order_date").resample("D").size().reset_index(name="shipments")
    left.plotly_chart(px.area(daily, x="order_date", y="shipments", title="Daily shipment volume", template="plotly_dark"), use_container_width=True)
    route = filtered.groupby(["origin", "destination"], as_index=False).shipping_cost.sum().nlargest(12, "shipping_cost")
    right.plotly_chart(px.bar(route, x="shipping_cost", y=route.origin + " → " + route.destination,
                              orientation="h", title="Highest-cost routes", template="plotly_dark"), use_container_width=True)
with carriers_tab:
    score = carrier_scorecard(filtered)
    st.plotly_chart(px.scatter(score, x="cost_per_km", y="on_time_rate", size="shipments", color="carrier",
                               hover_data=["avg_delay"], title="Cost vs reliability", template="plotly_dark"), use_container_width=True)
    st.dataframe(score.style.format({"on_time_rate":"{:.1f}%", "avg_delay":"{:.2f}", "total_cost":"€{:,.0f}", "cost_per_km":"€{:.2f}"}), use_container_width=True)
with forecast_tab:
    future, mae = forecast_daily_volume(filtered)
    st.metric("Validation MAE", f"{mae:.2f} shipments/day")
    st.plotly_chart(px.line(future, x="date", y="forecast", markers=True, title="14-day demand forecast", template="plotly_dark"), use_container_width=True)
with anomalies_tab:
    anomalies = detect_anomalies(filtered)
    flagged = anomalies[anomalies.anomaly]
    st.metric("Flagged shipments", len(flagged))
    st.dataframe(flagged[["shipment_id", "carrier", "origin", "destination", "shipping_cost", "actual_days", "anomaly_score"]], use_container_width=True)
with data_tab:
    st.dataframe(filtered, use_container_width=True, height=480)
    st.download_button("Download filtered CSV", filtered.to_csv(index=False), "logiscope_filtered.csv", "text/csv")

