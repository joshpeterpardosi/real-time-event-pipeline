# ADR 0002: Storage — ClickHouse vs. Postgres vs. SQLite

## Status
Accepted — 2026-08-14

## Context

The consumer needs to persist raw + flagged transactions somewhere both
Grafana (pipeline-health monitoring) and Streamlit (fraud-analyst view) can
query, at a write rate driven by the generator (up to hundreds of events/sec
in a demo burst) and a read pattern dominated by time-bucketed aggregations
(`toStartOfMinute(...)`, `avg(is_fraud)`, per-merchant counts).

## Decision Drivers

1. **Fit for time-bucketed analytical queries** — the exact query shape
   both dashboards need.
2. **Write throughput under batch inserts**, since the consumer batches
   rows (see `consumer/clickhouse_client.py`) rather than inserting
   per-event.
3. **Zero billing / local Docker** — must run as a free container image.
4. **Portfolio relevance** — the storage choice itself is a signal for a
   data-analyst-focused portfolio.

## Options Considered

### Option A: Postgres

**Pros**
- Extremely familiar, general-purpose relational store.
- Simple to query, wide tooling support.

**Cons**
- Row-oriented storage is not a natural fit for `GROUP BY toStartOfMinute(...)`-style
  aggregations at any real scale — every row is read in full even for
  aggregate-only queries.
- Doesn't carry any specific "built for real-time analytics" signal for a
  portfolio built around exactly that claim.

### Option B: SQLite

**Pros**
- Zero setup, zero container, a single file.

**Cons**
- Weak concurrent-write support — the consumer (writer) and two dashboards
  (readers) hitting the same SQLite file concurrently is exactly the
  contention pattern SQLite handles worst.
- Undermines the "real-time" claim of the project: a single-writer-lock
  file store is not what a real-time analytics backend looks like, which
  matters when the storage choice is part of what's being evaluated.

### Option C: ClickHouse

**Pros**
- Columnar storage, purpose-built for exactly this workload: time-bucketed
  aggregation queries over an append-heavy event stream.
- Batch inserts (the consumer buffers rows and flushes periodically) are
  ClickHouse's designed-for write pattern; the design doc's error-handling
  section (retry-with-backoff, then local buffer) exists specifically
  because ClickHouse is not suited to high-frequency single-row inserts —
  batching was a requirement driven by this choice, not incidental.
- Free, runs as a single Docker container locally.
- Directly supports both consumers: `grafana-clickhouse-datasource`
  (native protocol, port 9000) for Grafana, `clickhouse-connect` (HTTP,
  port 8123) for the consumer and Streamlit.

**Cons**
- Heavier mental model than Postgres for anyone unfamiliar with columnar
  stores (MergeTree engine, `ORDER BY` as a physical sort key rather than a
  query-time clause).
- The official Docker image ships with a security default that isn't
  obvious until you hit it: with no `CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD`
  set, the `default` user's *network* access is disabled entirely (only
  local/unix-socket access works) — see the fix in `docker-compose.yml`
  (`CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD` env vars) and `clickhouse/init.sql`
  for the `transactions` table DDL, both added after this surfaced during
  live verification.

## Comparison Summary

| Dimension                        | Postgres                | SQLite                  | ClickHouse                        |
|------------------------------------|----------------------------|----------------------------|---------------------------------------|
| Aggregation query fit               | Adequate, not optimized    | Poor at any real scale     | Purpose-built                         |
| Concurrent write + multi-reader     | Good                       | Poor (single-writer lock)  | Good (designed for this)              |
| Batch-insert friendliness           | Fine either way            | Fine either way            | Required — poor at per-row inserts    |
| Zero-billing / local Docker         | Yes                        | Yes (no container needed)  | Yes                                   |
| "Real-time analytics" portfolio fit | Weak signal                | Contradicts the claim      | Strong, on-brand signal               |

## Decision

**Use ClickHouse.** The dashboards' query shape (time-bucketed aggregation
over an append-only event stream) is precisely what ClickHouse is built
for, and the batch-insert requirement it imposes on the consumer is a
reasonable, well-understood constraint rather than a surprise. SQLite is
disqualified by the concurrent writer+readers pattern; Postgres would work
but carries none of ClickHouse's purpose-built advantage for this specific
workload, and "built for real-time analytics" is directly relevant to the
portfolio's own framing.

## Consequences

- `consumer/clickhouse_client.py` batches rows (flush on size or time
  interval) rather than inserting per-event — a direct requirement of this
  choice, not an independent design preference.
- The `transactions` table schema (`clickhouse/init.sql`) is loaded via
  `docker-entrypoint-initdb.d`, and `CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD`
  must be set in `docker-compose.yml` for any client — consumer, Streamlit,
  Grafana, or the integration test — to reach ClickHouse over the network.
- Anyone extending this pipeline to a genuinely OLTP-shaped workload (e.g.
  point lookups by `transaction_id` at high QPS) would want to reconsider —
  that isn't this project's access pattern, but it's the boundary of where
  this decision stops applying.

## Alternatives Rejected

- **Postgres** — works, but no specific advantage for this workload over
  ClickHouse, and weaker portfolio signal for a "real-time analytics"
  project.
- **SQLite** — rejected on concurrent-write grounds; a single-writer file
  store is the wrong architecture for a consumer + two dashboard readers
  hitting the same store simultaneously.
