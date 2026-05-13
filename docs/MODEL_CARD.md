# Model card

## Demand forecast

The volume model is a random-forest regressor trained on daily shipment counts. Features include a time index, weekday, month, one-day and seven-day lags, and seven-/28-day rolling means. The latest 20% of usable observations (bounded to 7–28 days) is held out chronologically. Reported MAE and MAPE refer only to that holdout.

Future points are generated recursively. The displayed interval adds and subtracts the 90th percentile of absolute holdout residuals. It is an empirical planning band, not a calibrated confidence interval. At least 28 calendar days and sufficient post-lag training rows are required.

## Shipment anomalies

Isolation Forest scores distance, weight, shipping cost, and actual transit days after robust scaling. The caller selects a contamination rate from greater than 0 through 0.25; 0.05 is the default. The explanation reason is the feature with the greatest robust distance from the dataset median.

An anomaly is a review signal only. It does not establish fraud, damage, SLA breach, or data error. Results should be validated by an operator with shipment context.

## Reproducibility and monitoring

Models use a fixed random seed and pinned dependencies. The current platform exposes backtest metrics but does not persist model versions or monitor drift. Before production use, teams should version datasets and artifacts, evaluate slices by route/carrier/season, define alert thresholds, and establish retraining and rollback procedures.
