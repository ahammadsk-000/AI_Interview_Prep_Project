# Phase 10 — Enterprise Scaling

Final backend phase. Status: **implemented**. Adds multi-tenancy, tiered quotas,
caching, and DB-scaling plumbing on top of the Phase 1–9 platform.

## 1. Multi-tenancy — Organizations & Mentor Dashboard
```
models/organization.py            Organization + OrganizationMembership (per-org role)
services/organization_service.py  create org · manage members · mentor dashboard
api/v1/endpoints/organizations.py /orgs CRUD + members + dashboard
migration 0008_organizations
```
An **Organization** groups users for team practice; membership carries a role
(`owner`/`admin`/`mentor`/`member`). The **mentor dashboard** (`GET /orgs/{id}/dashboard`)
aggregates each member's readiness by reusing the Phase-7 `AnalyticsService` — an org-level
rollup with average readiness and per-member stats. Authorization is role-based:
owners/admins manage members; owners/admins/mentors view the dashboard; non-members get 404.

**Additive by design:** existing user-scoped resources are unchanged. Organizations are a
parallel structure; full row-level org scoping of every resource is a clean follow-on
(add nullable `org_id` + RLS) without breaking today's APIs.

## 2. Subscription-tier quotas
```
domain/billing/plans.py     PLAN_LIMITS: plan → feature → daily limit (-1 = unlimited)
services/quota_service.py   QuotaService + CounterStore (Redis / in-memory)
deps.require_quota(feature) FastAPI dependency enforcing per-plan daily usage
```
Daily, per-(user, feature) counters checked against the user's plan. The counter store is
pluggable: **Redis** (atomic `INCR`+`EXPIRE`, shared across replicas) in prod, in-memory in
dev/tests. Applied to the multi-agent workflow (`free` = 5 runs/day → 6th returns **429
`quota_exceeded`**); the same dependency guards any metered feature.

## 3. Caching
```
core/cache.py   Cache port · InMemoryCache (TTL) · RedisCache (fail-open)
```
The analytics overview is cached per user (short TTL) — a hot, expensive read. In-memory
for a single replica / tests; Redis-backed and shared across replicas in production.

## 4. Database scaling
- **Connection pool**: tunable `pool_size` / `max_overflow` / `pool_recycle` on the async
  engine (front with **PgBouncer** in production for thousands of clients).
- **Read replica**: `READ_DATABASE_URL` + a second engine + `get_read_db` dependency.
  Pure-read consumers (the org mentor dashboard) route through the replica; read-your-writes
  paths (snapshot capture) stay on the primary for consistency.
- **Partitioning** (design): high-volume tables — `turns`, `coding_submissions`,
  `metric_snapshots`, `audit_logs`, `scores` — partition by month (`RANGE` on the timestamp).
  Implement as a Postgres-only migration that creates the partitioned parent + a rolling
  partition-creation job; analytics queries already filter by user/time so they prune cleanly.

## High availability
- **Stateless API** → N replicas behind the LB; all state in Postgres/Redis. HPA scales on
  CPU/memory (Phase 9). PodDisruptionBudget + `maxUnavailable: 0` rolling deploys.
- **Postgres**: managed HA (primary + sync standby) with read replicas for analytics.
- **Redis**: clustered/managed; used for cache, rate limiting, quotas, and Celery broker.
- **Code execution**: isolated, autoscaled Judge0 node pool, decoupled from the API.

## Testing
- `tests/test_cache.py` — get/set/delete + TTL expiry.
- `tests/test_quota.py` — free-plan blocking at limit, remaining decrement, pro vs free,
  enterprise unlimited, per-feature independence.
- `tests/test_organizations.py` — create (owner), add member, list, non-member 404,
  member-cannot-manage/view-dashboard (403), mentor dashboard rollup, auth, **live quota
  enforcement** (free agent workflow → 429 on the 6th call).
- **120 tests total green**; migrations 0001→0008 verified to apply in order; ruff clean.

## Security considerations
Org membership + role checks on every org operation (non-members 404, non-managers 403).
Quotas prevent abuse and enforce plan entitlements server-side. Cache keys are namespaced
per user; the Redis cache fails open (treated as a miss) so a cache outage degrades
performance, never correctness.

## What's intentionally deferred
- Full per-resource org scoping (`org_id` + Postgres RLS) — the org tables and auth are the
  foundation; resource scoping is the next additive migration.
- The partitioning migration is documented, not applied (Postgres-only; would no-op/blow up
  on the SQLite test path) — ship it as a guarded, dialect-aware migration in a real cluster.
