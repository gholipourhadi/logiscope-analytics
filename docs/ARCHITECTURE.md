# Architecture

## Design goals

LogiScope keeps business computation independent from web frameworks, rejects invalid input at one boundary, and returns stable typed results from each analytical service. The application is intentionally stateless: every request loads the configured dataset and derives a fresh validated frame.

## Layers

| Layer | Responsibility | Key modules |
|---|---|---|
| Domain | Canonical columns and validation policy | `app/domain/schema.py` |
| Core | Expected exception hierarchy | `app/core/exceptions.py` |
| Services | Ingestion, quality, metrics, ML, simulation | `app/services/` |
| Adapters | HTTP contracts and interactive UI | `app/api/`, `app/dashboard.py` |
| Delivery | CI, containers, developer commands | `.github/`, `Dockerfile`, `Makefile` |

## Request lifecycle

1. An adapter asks the ingestion service to read the configured CSV or upload.
2. Ingestion selects the canonical columns, coerces types, validates business rules, and derives stable features.
3. A service performs one bounded computation and returns a dataclass or data frame.
4. The adapter serializes the result or presents it without embedding analytical rules.
5. Expected domain failures become actionable HTTP 422 responses or dashboard messages.

## Modeling decisions

The forecast uses chronological rather than random validation to prevent future information from leaking into training. Iterative future predictions reuse generated lag values. The uncertainty band is the 90th percentile of absolute holdout residuals, which is simple, inspectable, and explicitly not a probabilistic guarantee.

Anomaly detection uses robust feature scaling before Isolation Forest. Each flagged row receives a reason code based on its largest median-relative feature deviation. This explanation is diagnostic rather than causal.

## Operational boundaries

The current service reloads a local CSV per request, appropriate for a demonstrator and small datasets. A production deployment should replace this adapter with versioned object storage or a database, cache immutable snapshots, execute models asynchronously, and export latency/error/model metrics.
