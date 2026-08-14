# Real-Time Event Pipeline — Fraud/Transaction Detection

## Status
Draft — 2026-08-14. Design approved by Josh in brainstorming session. Implementation deferred to a later session (desktop).

## Purpose

Portfolio project demonstrating an end-to-end real-time data pipeline: stream
ingestion, dual-mode fraud detection (rule-based + ML), analytical storage,
and two purpose-built dashboards (ops monitoring + fraud analyst view).
Target audience: hiring reviewers evaluating data engineering + data
analysis/visualization skill in combination.

## Constraints

- **Zero billing.** Entire stack runs locally via Docker Compose. No cloud
  accounts, no managed services.
- **Single maintainer**, portfolio timeline — favor debuggable, explainable
  components over maximum "buzzword" tooling.
- Must be runnable by a reviewer who clones the repo (`docker compose up`
  plus a documented seed/run step).

## Architecture

```
[Synthetic Generator] ──┐
                         ├──> Kafka topic `transactions` ──> Python Consumer
[Dataset Replay (Kaggle  ┘        (confluent-kafka or Faust)
 credit card fraud CSV)]                  │
                              ┌───────────┴───────────┐
                              │  Rule-based check       │  (amount threshold,
                              │  ML model scoring       │   velocity, geo
                              │  (combine → flag)       │   mismatch; XGBoost
                              └───────────┬───────────┘   pre-trained model)
                                          ▼
                                    ClickHouse (raw + flagged txn, batched insert)
                                          │
                            ┌─────────────┴─────────────┐
                            ▼                             ▼
                        Grafana                    Streamlit + Plotly
                    (pipeline health:              (fraud analyst view:
                    throughput, latency,            pattern, drilldown,
                    error rate)                      trend per user/merchant)
```

All services run as containers in `docker-compose.yml`: Kafka (or Redpanda
for a lighter footprint), ClickHouse, Grafana, the Python consumer, and the
Streamlit app.

## Components

### 1. Data sources (combo)
- **Synthetic generator** — Python script producing randomized transaction
  events with controllable fraud-pattern injection (for demoing specific
  detection scenarios).
- **Dataset replay** — Kaggle credit-card-fraud CSV replayed row-by-row onto
  the same Kafka topic, for a "real data" demo path and for training the ML
  model.
- Both publish to Kafka topic `transactions`, keyed by `user_id` for
  per-user partition ordering.

### 2. Stream processing — Kafka + Python consumer
- Chosen over Flink (heavier ops/learning-curve overhead for a solo
  timeline) and ksqlDB (less flexible for stateful fraud logic like rolling
  windows). Recommendation accepted.
- Consumer logic kept decoupled from Kafka plumbing, so it could later be
  ported into a PyFlink job without a redesign, if desired as a stretch
  goal.

### 3. Fraud detection logic — combo rule-based + ML
- **Rule-based layer**: amount threshold, velocity (>N transactions/minute
  per user, sliding window in-memory or Redis-backed), geo mismatch vs.
  user history.
- **ML layer**: model (e.g. XGBoost) trained offline against the Kaggle
  dataset, loaded at consumer startup, scores each event's fraud
  probability.
- **Combine**: flag `is_fraud = true` if rule triggers OR ML score exceeds
  threshold. Persist `fraud_reason` (rule / ml / both) and
  `confidence_score`.

### 4. Storage — ClickHouse
- Chosen over Postgres (less analytics-native) and SQLite (weak concurrent
  writes, doesn't support the "real-time" claim). Free, runs in Docker,
  purpose-built for real-time analytical queries.
- Writes are batched (buffer N events or flush every X seconds) — ClickHouse
  is not suited to high-frequency single-row inserts.

### 5. Dashboards — combo Grafana + Streamlit/Plotly
- **Grafana**, connected to ClickHouse via the official ClickHouse
  datasource plugin: pipeline health (throughput, latency, error rate),
  5-10s refresh interval. Also serves as a hands-on test of Grafana itself.
- **Streamlit + Plotly**: custom fraud-analyst view — pattern exploration,
  per-user/merchant trend, drilldown. This is the primary dataviz showcase
  surface, reflecting the project owner's data-analyst/dataviz focus.

### 6. Alerting
- **Dashboard-only.** No external notification channel (no Slack/webhook).
  Flags are visible in both dashboards; this was an explicit scope decision
  to keep the alerting surface simple.

## Data Flow

1. Generator/replay script produces transaction JSON → publishes to Kafka
   topic `transactions` (key: `user_id`).
2. Python consumer subscribes, and per event:
   - Runs the rule engine (threshold / velocity / geo checks).
   - Runs ML scoring (pre-trained model, loaded via joblib/pickle).
   - Combines both into a single flag + reason + confidence score.
3. Consumer batch-writes (raw txn + flag + score) into ClickHouse.
4. Grafana and Streamlit query ClickHouse directly (read-only), auto-refreshing.

## Error Handling

- **Offset commits**: manual, committed only after a successful ClickHouse
  insert (at-least-once delivery, avoids data loss on consumer crash).
- **Malformed events** (invalid JSON / missing fields): skipped, routed to a
  Kafka `dead_letter` topic, logged — consumer must not crash.
- **ClickHouse insert failure**: retried with backoff (3 attempts); on
  continued failure, buffered locally and logged as an error (no external
  alert, per the dashboard-only decision).
- **ML model load failure at startup**: consumer fails fast and refuses to
  start, since ML scoring is a required part of the combo detection logic,
  not an optional enhancement.

## Testing

- **Unit tests**: rule engine logic (thresholds, velocity calculation) and
  the ML scoring wrapper — pytest, with Kafka/ClickHouse mocked.
- **Integration test**: full stack via `docker compose up`, generator sends
  a fixed set of sample transactions including known-fraud patterns, assert
  correct flags land in ClickHouse.
- **Model validation**: replay the Kaggle dataset offline to check
  precision/recall before the model is used for live scoring.

## Repo Structure

```
real-time-event-pipeline/
├── docker-compose.yml
├── README.md              (architecture diagram, run instructions, dashboard screenshots)
├── generator/              (synthetic + replay scripts)
├── consumer/                (Kafka consumer, rule engine, ML scoring)
├── ml/                       (training notebook/script, model artifact)
├── dashboards/
│   ├── grafana/              (provisioned dashboard json)
│   └── streamlit/            (app.py, plotly charts)
├── tests/
└── docs/
    ├── superpowers/specs/    (this design doc)
    └── adr/                  (individual decision records, as needed)
```

README is a first-class deliverable: architecture diagram, GIF/screenshot of
both dashboards, "run in 3 commands" quick start.

## Out of Scope (explicit)

- Cloud deployment of any kind.
- External alerting (Slack/webhook/email).
- Flink/ksqlDB stream processing (noted as a possible later upgrade path,
  not part of this design).

## Next Step

Implementation is deferred to a later session. When resumed, invoke the
`writing-plans` skill against this spec to produce a step-by-step
implementation plan before writing code.
