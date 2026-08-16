# ADR 0003: Fraud Detection — Rule-Based vs. ML vs. Combo (and ML Feature Scope)

## Status
Accepted — 2026-08-14

## Context

The pipeline has two independent data sources feeding the same
`transactions` Kafka topic: a synthetic generator (controllable fraud
patterns: amount, velocity, geo) and a replay of Kaggle's "Credit Card
Fraud Detection" CSV (real, anonymized transaction data with PCA features
`V1`–`V28` and a ground-truth `Class` label). The detection logic has to
decide, per event, whether it's fraudulent, and needs to demonstrate both
rule-engineering and applied-ML skill for portfolio purposes.

A second, narrower question surfaced once the two data sources were
compared directly: the synthetic generator emits `amount`/`merchant`/
`country`/`user_id`, while the Kaggle dataset's predictive signal lives
entirely in 28 anonymized PCA features specific to that dataset's
originating bank. Those feature spaces don't overlap, so a single detection
strategy can't score both sources through the same mechanism.

## Decision Drivers

1. **Coverage of both skill signals** — rule-engineering (explicit,
   explainable) and applied ML (model training + offline validation) are
   both relevant to the portfolio's purpose; using only one leaves a gap.
2. **Explainability where it's needed** — a `fraud_reason` string
   (`"rule:amount_threshold,ml"`) needs to trace back to *why* an event was
   flagged, which rules-only trivially gives and ML-only does not.
3. **No answer-leakage** — the Kaggle `Class` label must never appear in
   the live event payload; a "real-time" detector that has secretly seen
   the ground truth isn't demonstrating anything.
4. **Feature availability is source-dependent** — the synthetic generator
   cannot fabricate the Kaggle dataset's `V1`–`V28` PCA features without
   inventing meaningless numbers, since those features are specific to a
   bank's own internal transformation of real transaction data.

## Options Considered

### Option A: Rule-based only

**Pros**
- Fully explainable, trivial to reason about and test.
- No training data or offline validation pipeline needed.

**Cons**
- Doesn't demonstrate applied ML at all — a real gap for a portfolio
  explicitly meant to show a combination of data engineering and data
  science skill.
- Static thresholds don't adapt to subtler fraud patterns the way a
  trained classifier can.

### Option B: ML only

**Pros**
- Showcases model training, offline validation, and live scoring.

**Cons**
- No rule layer means no cheap, explicit catch for obviously-fraudulent
  patterns (e.g. an absurd amount) — everything routes through model
  inference even when a one-line check would suffice.
- Harder to explain a specific flag to a non-technical reviewer than
  `"rule:amount_threshold"` is.
- The synthetic generator's fields (`amount`, `merchant`, `country`) don't
  match the Kaggle model's PCA feature space, so an ML-only design would
  either need to retrain a second model against synthetic-shaped features
  (extra scope with little payoff) or leave synthetic events unscored
  entirely.

### Option C: Combo — rule engine + ML scorer, combined

**Pros**
- Demonstrates both skills: `consumer/rules.py` (amount, velocity, geo
  mismatch, all independently unit-tested) and `ml/train.py` +
  `consumer/ml_scorer.py` (XGBoost trained offline, `precision`/`recall`
  gated in `ml/validate.py` before the model is trusted for live scoring).
- `consumer/combine.py` produces a single `is_fraud` flag with a
  `fraud_reason` that names every contributing signal (`"rule:velocity,ml"`),
  giving explainability *and* model-driven scoring together.
- Naturally resolves the feature-availability mismatch: ML scoring applies
  only to `source="replay"` events (see the schema's optional `features`
  field, `TransactionEvent.features: list[float] | None`), since those are
  the only events carrying the Kaggle PCA features the model was trained
  on. Synthetic events are judged by the rule engine alone.
- The Kaggle `Class` label never enters the live event payload —
  `generator/replay.py` builds `TransactionEvent` from the CSV row without
  it; `ml/train.py` reads the CSV directly for offline training instead,
  so there's no path for the ground truth to leak into "real-time" scoring.

**Cons**
- More moving parts than either option alone: two detection layers to
  keep independently testable and to combine correctly (`consumer/combine.py`
  has 5 unit tests covering rule-only, ML-only, both, and neither).
- The asymmetry (only replay events get ML-scored) has to be documented
  clearly, or it reads as an oversight rather than a deliberate choice —
  hence this ADR.

## Decision

**Use the combo: rule engine + ML scorer, combined into one fraud flag.**
ML scoring is restricted to `source="replay"` events, since the Kaggle
PCA features (`V1`–`V28`) are the only ones the trained model understands
and the synthetic generator cannot meaningfully reproduce them. Synthetic
events are judged by the rule engine only. `MLScorer.score()` returns
`None` when `features` is absent, and `consumer/combine.py` treats a
`None` ML score as "no ML signal" rather than an error — so the two
sources exercise the two different (and complementary) parts of the combo
design, rather than one design being incompletely applied everywhere.

## Consequences

- `shared/schema.py`'s `TransactionEvent.features` is optional and only
  populated by `generator/replay.py`, never by `generator/synthetic.py` —
  this is the schema-level expression of the decision, not an
  implementation detail to fix later.
- `consumer/ml_scorer.py` fails fast (raises `RuntimeError`) if the model
  fails to load at consumer startup, per the design doc's global
  constraint — ML scoring is a required part of the combo, not an optional
  enhancement that can silently degrade.
- `ml/validate.py` enforces a precision/recall bar (`MIN_PRECISION = 0.80`,
  `MIN_RECALL = 0.70`) before a trained model is considered usable;
  `ml/train.py` asserts this at the end of training. The trained model in
  this repo clears the bar at precision 0.856 / recall 0.786 against the
  Kaggle held-out test split.
- That bar is measured at `ML_FRAUD_THRESHOLD`, the same constant the consumer
  flags on, defined once in `shared/thresholds.py` and imported by both.
  `validate` originally called `model.predict`, which applies the implicit 0.5,
  while `combine` flagged at 0.7 — so the gate was certifying an operating point
  the pipeline never ran. On the current model the gap was one false positive
  (precision 0.846 at 0.5 against 0.856 at 0.7), harmless here only because this
  model separates cleanly. A less separable model could clear the bar at 0.5 and
  fail it at 0.7 with nothing to catch it, so the two now share one definition
  and a test asserts they agree.
- Anyone extending the synthetic generator to emit fields that map onto a
  retrained model's feature space could lift this restriction — it's a
  data-availability constraint, not a permanent architectural one.

## Alternatives Rejected

- **Rule-based only** — leaves out the applied-ML signal the portfolio is
  meant to demonstrate.
- **ML only** — no cheap explicit-rule catch, weaker explainability per
  flag, and doesn't resolve the synthetic/Kaggle feature-space mismatch any
  better than the combo does.
