# Shipment data contract

LogiScope accepts UTF-8 CSV files with one row per shipment. Column names are case-sensitive.

| Column | Type | Constraint |
|---|---|---|
| `shipment_id` | string | Required, non-empty, unique by default |
| `order_date` | date/datetime | Required and parseable |
| `origin` | string | Required and non-empty |
| `destination` | string | Required and non-empty |
| `carrier` | string | Required and non-empty |
| `distance_km` | number | Finite and greater than zero |
| `weight_kg` | number | Finite and greater than zero |
| `shipping_cost` | number | Finite and non-negative |
| `planned_days` | number | Between 0 and 365 by default |
| `actual_days` | number | Between 0 and 365 by default |
| `status` | string | Required and non-empty |

Same-city movements are accepted because last-mile shipments can legitimately have the same origin and destination city. Deployments operating only inter-city lanes can reject them through `ValidationPolicy(allow_same_origin_destination=False)`.

The ingestion service ignores extra input columns and emits only canonical plus derived columns. Invalid datasets are rejected atomically; LogiScope does not silently drop malformed rows.
