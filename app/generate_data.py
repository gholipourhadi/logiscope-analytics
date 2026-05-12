from pathlib import Path

import numpy as np
import pandas as pd


def generate(path: str = "data/sample_shipments.csv", rows: int = 2500) -> None:
    rng = np.random.default_rng(42)
    cities = np.array(["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Leipzig"])
    carriers = np.array(["DHL", "DB Schenker", "Kuehne+Nagel", "UPS"])
    dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, rows), unit="D")
    distance = rng.integers(80, 950, rows)
    weight = rng.lognormal(4.3, .75, rows).round(1)
    planned = np.select([distance < 250, distance < 600], [1, 2], default=3)
    carrier_delay = {"DHL": .20, "DB Schenker": .35, "Kuehne+Nagel": .28, "UPS": .16}
    selected = rng.choice(carriers, rows)
    extra = np.array([rng.binomial(2, carrier_delay[c]) for c in selected])
    actual = planned + extra
    cost = (18 + distance * .42 + weight * .16 + rng.normal(0, 18, rows)).clip(15).round(2)
    anomaly_idx = rng.choice(rows, 25, replace=False)
    cost[anomaly_idx] *= 2.8
    df = pd.DataFrame({
        "shipment_id": [f"SHP-{i:06d}" for i in range(1, rows + 1)],
        "order_date": dates, "origin": rng.choice(cities, rows),
        "destination": rng.choice(cities, rows), "carrier": selected,
        "distance_km": distance, "weight_kg": weight, "shipping_cost": cost,
        "planned_days": planned, "actual_days": actual,
        "status": np.where(actual <= planned, "On time", "Delayed"),
    }).sort_values("order_date")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    generate()

