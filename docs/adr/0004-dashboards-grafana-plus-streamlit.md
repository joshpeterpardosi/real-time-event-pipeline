# ADR 0004: Dashboards — Grafana + Streamlit (Dual, Not Either/Or)

## Status
Accepted — 2026-08-14

## Context

The pipeline produces two distinct kinds of information reviewers and an
imagined "analyst user" would want to see: operational pipeline health
(is data flowing, what's the throughput and fraud-flag rate) and
analytical drill-down into flagged transactions (which merchants, what
amounts, why was each one flagged). Both read from the same ClickHouse
`transactions` table but serve different audiences and different levels of
customization.

## Decision Drivers

1. **Portfolio focus** — the project owner's stated priority is
   data-visualization skill specifically, over general UI/UX; the
   dashboard layer is not incidental plumbing, it's part of what's being
   evaluated.
2. **Two genuinely different jobs** — "is the pipeline healthy" (ops
   monitoring, standard time-series panels, auto-refresh) and "explore
   flagged transactions" (custom charts, a drill-down table, per-merchant
   breakdowns) don't want the same tool's strengths.
3. **Hands-on tool experience** — trying Grafana firsthand (provisioning a
   ClickHouse datasource, building panels) was an explicit goal alongside
   shipping the feature.

## Options Considered

### Option A: Grafana only

**Pros**
- Real-time auto-refresh, purpose-built for exactly the "pipeline health"
  half of the requirement.
- Minimal code — panels are JSON, not a hand-built app.

**Cons**
- A fraud-analyst view built entirely from Grafana panels caps out on
  customization compared to a purpose-written Python app — drill-down
  tables, custom chart layouts, and bespoke framing (e.g. "flagged
  transactions by merchant") are all more naturally expressed in
  Streamlit + Plotly than in Grafana's panel model.
- Doesn't showcase the project owner's specific dataviz-building skill —
  it showcases configuring someone else's tool instead.

### Option B: Streamlit + Plotly only

**Pros**
- Full control over layout and framing; the whole point of the
  fraud-analyst view.
- Directly demonstrates custom dataviz code, which is the portfolio's
  stated priority.

**Cons**
- Reinventing ops-monitoring plumbing (auto-refreshing throughput/error
  panels) in Streamlit is pure duplication of what Grafana already does
  well and for free — no reason to hand-build that half.
- Loses the "test-drive Grafana" goal entirely.

### Option C: Both — Grafana for ops, Streamlit for analysis

**Pros**
- Each tool does the half it's actually good at: Grafana
  (`dashboards/grafana/provisioning/`) owns pipeline health (throughput,
  fraud-flag rate, 5s auto-refresh), Streamlit
  (`dashboards/streamlit/app.py`) owns the fraud-analyst view (flagged-by-merchant
  bar chart, amount-over-time scatter colored by `is_fraud`, a drill-down
  table with `fraud_reason`/`confidence_score`).
- Satisfies both goals directly instead of trading one off against the
  other: dataviz showcase (Streamlit) and hands-on Grafana experience
  (Grafana), rather than picking one tool and losing the other's value.

**Cons**
- Two dashboard stacks to build, provision, and keep working instead of
  one — more surface area (e.g. the `grafana-clickhouse-datasource` plugin
  isn't bundled by default and needs `GF_INSTALL_PLUGINS` set explicitly;
  this was missed initially and only surfaced during live verification).
- A reviewer has to open two URLs instead of one to see the full picture.

## Comparison Summary

| Dimension                          | Grafana only            | Streamlit only          | Both                              |
|--------------------------------------|----------------------------|----------------------------|----------------------------------------|
| Ops/pipeline-health monitoring       | Strong, native fit         | Reinvented, wasted effort  | Owned by Grafana                        |
| Custom fraud-analyst drill-down      | Capped by panel model      | Full control               | Owned by Streamlit                      |
| Dataviz skill demonstrated           | Weak (config, not code)    | Strong                     | Strong, where it counts (Streamlit)     |
| Hands-on Grafana experience          | Yes                        | No                         | Yes                                     |
| Setup/maintenance surface            | Single stack               | Single stack               | Two stacks                              |

## Decision

**Run both, each doing the half it's suited for.** Grafana owns pipeline
operational health; Streamlit + Plotly owns the fraud-analyst exploration
view. This isn't hedging between two equally-valid choices — the two
dashboards answer different questions for different audiences, and
building both was cheap relative to the value of not compromising either
one, plus it satisfied the explicit goal of getting hands-on with Grafana
without giving up the custom dataviz showcase.

## Consequences

- Two provisioning surfaces to keep correct: `dashboards/grafana/provisioning/datasources/clickhouse.yml`
  (must pin a stable `uid` — an unpinned, auto-generated UID broke panel
  queries across a container recreate during live verification, fixed by
  setting `uid: clickhouse` explicitly) and `dashboards/streamlit/app.py`
  (plain Python, no provisioning step, just a running container).
- `docker-compose.yml`'s `grafana` service needs
  `GF_INSTALL_PLUGINS: grafana-clickhouse-datasource` — the plugin isn't
  bundled in the base image, and its absence produces a working container
  with a broken datasource until this is set.
- A reviewer running the full quick-start opens two ports (3000 and 8501)
  rather than one; this is called out explicitly in the README's dashboards
  section rather than left implicit.

## Alternatives Rejected

- **Grafana only** — would have skipped the project's stated dataviz
  priority in favor of pure ops tooling.
- **Streamlit only** — would have skipped the explicit goal of hands-on
  Grafana experience, and duplicated ops-monitoring functionality Grafana
  provides natively.
