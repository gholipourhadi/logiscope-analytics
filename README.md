# LogiScope Analytics

LogiScope is a logistics decision-support platform built around a strict shipment data contract. It validates operational data before analysis, exposes deterministic KPIs and scorecards, detects explainable anomalies, backtests a demand forecast, and simulates capacity and cost scenarios through both a FastAPI service and a Streamlit dashboard.

The repository deliberately separates ingestion, analytics, API, and presentation concerns. Every capability listed below is implemented and covered by automated tests.

## Implemented capabilities

- Strict CSV ingestion with schema, null, identifier, numeric, transit-time, and safety-limit validation.
- Derived operational features including delay, on-time status, route, unit costs, month, and weekday.
- Data-quality profiling with duplicate, missing-value, same-city, date-range, freshness, and quality-score signals.
- Fleet-wide KPIs plus carrier and route scorecards with reliability, cost, and composite rankings.
- Explainable multivariate anomaly detection using robust scaling and Isolation Forest reason codes.
- Daily shipment forecasting with lag/rolling features, chronological backtesting, MAE/MAPE, and 90% empirical intervals.
- Cost, volume, transit-improvement, and daily-capacity scenario simulation.
- Versioned FastAPI endpoints with validated parameters and domain-aware error responses.
- Interactive Streamlit views for operations, forecasts, anomalies, scenarios, quality, and export.
- Reproducible sample-data generation, Docker images, Compose services, Ruff, Black, pytest, and Python 3.11/3.12 CI.

## Architecture

```text
CSV / upload
    │
    ▼
ingestion + validation ──► normalized shipment frame
    │                              │
    ├── quality                    ├── metrics / scorecards
    ├── anomalies                  ├── forecasting
    └── scenarios                  └── derived features
                   │
             FastAPI + Streamlit
```

Service functions are framework-independent and accept validated pandas data frames. FastAPI and Streamlit are adapters; neither contains model logic. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md), and [docs/MODEL_CARD.md](docs/MODEL_CARD.md).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make check
```

Start either interface:

```bash
make api        # OpenAPI at http://localhost:8000/docs
make dashboard  # Dashboard at http://localhost:8501
```

Or run both using containers:

```bash
docker compose up --build
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Service and dataset readiness |
| `GET` | `/api/v1/kpis` | Portfolio-level operational KPIs |
| `GET` | `/api/v1/quality` | Data-quality profile |
| `GET` | `/api/v1/carriers` | Ranked carrier scorecard |
| `GET` | `/api/v1/routes` | Route performance with volume threshold |
| `GET` | `/api/v1/anomalies` | Ranked, reason-coded shipment anomalies |
| `GET` | `/api/v1/forecast` | Backtested 1–90 day demand forecast |
| `POST` | `/api/v1/scenarios` | Cost and capacity scenario simulation |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/scenarios \
  -H 'content-type: application/json' \
  -d '{"volume_change_percent":20,"fuel_surcharge_percent":8,"transit_improvement_days":1,"daily_capacity":20}'
```

## Quality gates

CI executes three independent jobs: formatting/lint/byte-compilation on Python 3.12, plus the complete test suite on Python 3.11 and 3.12. Tests cover ingestion failures, KPI and scorecard correctness, quality reporting, model constraints, scenario boundaries, API responses, and missing-dataset behavior.

## Scope and limitations

- The bundled CSV is synthetic and suitable for demonstrations and regression tests, not business decisions.
- Forecasts are univariate volume estimates; they do not model promotions, holidays, weather, or causal effects.
- Anomaly labels identify statistical outliers, not confirmed fraud or operational failures.
- Scenario outputs are deterministic planning estimates, not an optimization solver.
- Authentication, multi-tenancy, persistent uploads, background jobs, and model monitoring are intentionally out of scope and are not claimed as implemented.

## Roadmap

- Persist versioned datasets and model runs in PostgreSQL/object storage.
- Add authenticated tenants and role-based access controls.
- Introduce external regressors and rolling-origin model selection.
- Add async jobs, metrics export, drift alerts, and deployment manifests.

## License

MIT
