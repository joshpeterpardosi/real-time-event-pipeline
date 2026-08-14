# Real-Time Event Pipeline — Fraud/Transaction Detection

End-to-end real-time pipeline: stream ingestion, dual-mode fraud detection
(rule-based + ML), analytical storage, and two dashboards. Full design:
[docs/design/2026-08-14-real-time-event-pipeline-design.md](docs/design/2026-08-14-real-time-event-pipeline-design.md).

## Architecture

```
[Synthetic Generator] ──┐
                         ├──> Kafka topic `transactions` ──> Python Consumer
[Dataset Replay (Kaggle  ┘        (confluent-kafka)
 credit card fraud CSV)]                  │
                              ┌───────────┴───────────┐
                              │  Rule-based check       │  (amount, velocity, geo)
                              │  ML model scoring        │  (XGBoost, replay-only)
                              └───────────┬───────────┘
                                          ▼
                                    ClickHouse (raw + flagged txn)
                                          │
                            ┌─────────────┴─────────────┐
                            ▼                             ▼
                        Grafana                    Streamlit + Plotly
                    (pipeline health)              (fraud analyst view)
```

## Run it

1. Download `creditcard.csv` from Kaggle's "Credit Card Fraud Detection"
   dataset into `ml/data/creditcard.csv`.
2. Train the model: `python -m ml.train ml/data/creditcard.csv ml/model.joblib`
3. `docker compose up -d`
4. Seed traffic:
   - Synthetic: `docker compose run --rm generator synthetic --rate 5 --fraud-ratio 0.05`
   - Replay: `docker compose run --rm generator replay --csv ml/data/creditcard.csv`
5. Grafana: http://localhost:3000 (pipeline health) · Streamlit: http://localhost:8501 (fraud analyst view)

## Tests

Unit tests (no external services required):

```
python -m venv .venv && .venv/Scripts/pip install -r consumer/requirements.txt -r generator/requirements.txt -r ml/requirements.txt pytest
.venv/Scripts/python -m pytest
```

Integration test (requires `docker compose up -d` first):

```
.venv/Scripts/python -m pytest -m integration
```

## Dashboards

(screenshots go here once captured)
