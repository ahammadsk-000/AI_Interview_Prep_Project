# Module 13 — Analytics Dashboard

Bounded context: **Analytics**. Status: **implemented (Phase 7)**.

## Architecture
```
api/v1/endpoints/analytics.py     ← overview · trends · history · snapshots
services/analytics_service.py     ← AnalyticsService (compose repo + aggregations)
repositories/analytics.py         ← cross-table read queries (per user)
domain/analytics/aggregations.py  ← pure trend bucketing + summaries (DB-free, tested)
domain/analytics/enums.py         ← MetricName · Bucket · HistoryKind
models/analytics.py + migration 0007   ← MetricSnapshot (captured readiness over time)
```

**Design choice — read-side composition over the existing tables.** The dashboard is
pure aggregation: it reads `scores`, `coding_submissions`, `ats_reports`,
`interview_sessions`, `agent_runs`, and `metric_snapshots` (all scoped to the user) and
folds them with **framework-free helpers**. Bucketing is done in Python (not SQL
`date_trunc`) so the same code runs on Postgres and SQLite and is unit-testable. The
polymorphic `scores` table (from Phase 5) was designed for exactly this.

## What the dashboard provides (Module 13 requirements)
- **Interview history** — recent sessions with type, status, and average score.
- **Performance trends** — readiness / ATS / coding / communication / technical over
  time, bucketed by day or week, with a summary (avg, min, max, delta, direction).
- **Skill / dimension breakdown** — averaged answer-grade dimensions (technical,
  communication, completeness, confidence).
- **ATS improvement trend** — score series + first→latest improvement delta.
- **Coding scores** — submissions, acceptance rate, average/best readiness.
- **Readiness metrics** — latest composite readiness (from the multi-agent feedback, or
  computed from available signals) plus a captured snapshot series.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/analytics/overview` | bearer | One-call dashboard: totals + readiness + coding/ATS/interview stats + dimensions |
| GET | `/analytics/trends?metric=&bucket=` | bearer | Time series + summary for a metric |
| GET | `/analytics/history?kind=&limit=` | bearer | Recent activity of a kind (interview/answer/behavioral/coding/ATS) |
| POST | `/analytics/snapshots` | bearer | Capture a metric snapshot (defaults to current readiness) |

## Readiness over time
`metric_snapshots` stores captured composite readiness so the **trend survives** even
as raw rows are archived. Snapshots are captured on demand (the endpoint) or, in
production, by a scheduled Celery job after each session — the readiness trend reads
this table; per-domain trends (ATS, coding, communication) read their own timestamped
rows live.

## Database schema
`metric_snapshots` — `user_id`, `metric`, `value`, `captured_at` (indexed on user +
metric; partition by month at scale). Migration `0007_analytics.py`. No other new
tables — analytics reads what earlier phases already write.

## Testing
- `tests/test_aggregations.py` — summary direction/delta, day & week bucketing
  (same-day averaging, chronological ordering), dimension averaging.
- `tests/test_analytics_api.py` — seeds real activity (graded answers, two ATS
  analyses, a coding submission, an interview) then asserts overview totals + coding/ATS/
  interview stats + dimensions + readiness; communication & ATS trends; snapshot capture
  + readiness trend; interview history; empty-user overview; auth.
- **97 tests total green**; migrations 0001→0007 verified to apply in order.

## Security considerations
Every query is scoped to the authenticated user — no cross-tenant aggregation. `ats_reports`
(which has no `user_id`) is filtered by joining `resumes` on ownership. Auth required on
all endpoints.

## Scalability considerations
Read-heavy and cache-friendly (overview/trends are good Redis-cache candidates with short
TTLs). Heavy historical aggregation precomputes into `metric_snapshots` via Celery; live
queries stay bounded. High-volume source tables (`scores`, `coding_submissions`,
`metric_snapshots`) partition by month; analytics can run against read replicas.

## Deployment strategy
No new packages. Optionally schedule a Celery beat job to capture readiness snapshots per
user on a cadence; the frontend (later phase) renders charts from these endpoints.
