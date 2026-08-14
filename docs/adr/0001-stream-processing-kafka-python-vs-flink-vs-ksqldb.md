# ADR 0001: Stream Processing — Kafka + Python Consumer vs. Flink vs. ksqlDB

## Status
Accepted — 2026-08-14

## Context

The pipeline needs to consume `transactions` events off Kafka (Redpanda),
evaluate a rule engine and an ML model against each event, and write the
result to ClickHouse. This is a solo portfolio project on a fixed timeline,
zero-billing (local Docker only), and the fraud logic itself (rolling
velocity windows, feature engineering for the ML scorer) is stateful and
non-trivial. Reviewers are expected to read the source, not just see it
pass a demo.

## Decision Drivers

1. **Time-to-working-pipeline** — solo maintainer, limited timeline.
2. **Debuggability** — a single person needs to trace and fix logic without
   fighting a distributed runtime's operational model.
3. **Explainability as a portfolio artifact** — the detection logic should
   read as plain, reviewable code, since that's the actual subject being
   evaluated (a fraud-detection *pipeline*, not a *Flink deployment*).
4. **Resume/keyword value** — some weight, but secondary to the above three.
5. **Upgrade path** — should not foreclose porting to a heavier engine later.

## Options Considered

### Option A: Kafka + Flink (PyFlink)

Flink is the industry-standard stream processing engine for exactly this
kind of stateful, windowed processing.

**Pros**
- Genuine "big data" keyword weight on a resume.
- Built-in primitives for windowing, state backends, exactly-once
  processing — the velocity-check logic wouldn't need to be hand-rolled.

**Cons**
- Real operational overhead: job manager/task manager topology, state
  backend configuration, a steeper debugging loop (job graphs, checkpoints)
  than a plain Python process.
- For a fixed-timeline solo project, that overhead competes directly with
  time spent on the actual fraud logic and dashboards — the parts a
  reviewer actually looks at.
- Rule/ML logic buried inside a Flink job is harder to unit test in
  isolation compared to plain functions.

### Option B: Kafka + ksqlDB

SQL-based stream processing directly on Kafka topics.

**Pros**
- Very low setup ceremony; queries are plain SQL.
- Reasonable fit for an analyst background.

**Cons**
- The fraud logic isn't naturally SQL-shaped: per-user rolling velocity
  windows, a `predict_proba` call against a joblib-loaded XGBoost model,
  and multi-signal combination (rule reasons + ML score → single flag) are
  all straightforward in a few lines of Python and awkward or impossible to
  express cleanly in ksqlDB.
- ML inference specifically has no natural home in ksqlDB — it would have
  to shell out to something else anyway, defeating the simplicity argument.

### Option C: Kafka + Python consumer (confluent-kafka)

A plain Python process: `Consumer.poll()` loop, manual offset commits,
rule engine and ML scorer as plain importable functions/classes.

**Pros**
- Every piece of logic (rule engine, ML scorer, combine function, message
  processing) is a small, independently unit-testable Python module — see
  `consumer/rules.py`, `consumer/ml_scorer.py`, `consumer/combine.py`,
  `consumer/consumer.py`.
- Debugging is just debugging Python: no job graph, no separate runtime UI
  to reason about failures through.
- Minimal dependency and image footprint (see ADR 0003's related note on
  `xgboost` vs `xgboost-cpu`).
- Manual offset commits (commit only after a successful ClickHouse insert)
  are simple to express directly, matching the at-least-once delivery
  requirement in the design doc.

**Cons**
- No free windowing/state-backend primitives — velocity tracking is
  hand-rolled (`collections.deque` per user, evaluated against a time
  window) rather than a framework construct.
- Weaker resume-keyword signal than Flink specifically.
- No built-in exactly-once semantics; the pipeline accepts at-least-once
  with idempotency-adjacent design (offset commits gated on successful
  writes) instead.

## Comparison Summary

| Dimension                          | Flink (PyFlink)        | ksqlDB                | Python consumer          |
|-------------------------------------|--------------------------|--------------------------|-----------------------------|
| Setup/operational overhead          | High                      | Low                       | Low                          |
| Fits stateful rule+ML logic         | Yes (native)              | Poorly (not SQL-shaped)   | Yes (plain code)             |
| ML inference (`predict_proba`)      | Possible, extra wiring    | No natural fit            | Direct, trivial              |
| Unit-testability of logic           | Harder (embedded in job)  | N/A                       | Easy (plain functions)       |
| Debuggability, solo maintainer      | Steeper                   | Easy                      | Easiest                      |
| Resume/keyword weight               | Highest                   | Medium                    | Lower                        |

## Decision

**Use Kafka (Redpanda) with a plain Python consumer** (`confluent-kafka`).
The fraud logic is the actual subject of this portfolio piece — it needs to
be legible, testable, and debuggable by one person on a fixed timeline.
Neither Flink's operational weight nor ksqlDB's SQL-shaped constraints pay
for themselves here; the plain-Python option lets the detection logic live
as small, independently tested modules (`rules.py`, `ml_scorer.py`,
`combine.py`), which is a stronger signal of engineering judgment than a
Flink job wrapping the same logic would be.

## Consequences

- Velocity/geo checks are hand-rolled in `consumer/rules.py` using
  in-memory per-user state (`deque`/dict) rather than a framework-provided
  windowing primitive. This does not survive a consumer restart — acceptable
  for a demo/portfolio pipeline, would need externalizing (e.g. Redis) for
  production use.
- Consumer logic is kept decoupled from Kafka plumbing (`process_message()`
  takes a raw string and returns a plain dict), so a future port to PyFlink
  is possible without redesigning the detection logic itself, if the
  project ever needs that upgrade path.

## Alternatives Rejected

- **Flink** — operational overhead not justified for a solo, fixed-timeline
  portfolio project where the detection logic itself is the thing being
  evaluated.
- **ksqlDB** — fraud logic (stateful velocity windows, ML inference) isn't
  SQL-shaped; would require bolting on external processing anyway.
