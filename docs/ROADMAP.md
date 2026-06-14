# Implementation Roadmap

Phased delivery. Each phase ships working, tested, migration-backed code. **Existing functionality never breaks** — new modules are additive, behind clean interfaces, with backward-compatible migrations.

| Phase | Scope | Status |
|---|---|---|
| **1** | System architecture · monorepo · backend setup · **Auth & User Management (RBAC, JWT, OAuth scaffolding, sessions, subscriptions)** | ✅ **Done** |
| **2** | **Resume Analyzer · ATS Optimization Engine (parse PDF/DOCX/TXT, deterministic scoring, skill/keyword gap, JD matching, LLM rewrite, résumé versioning)** | ✅ **Done** |
| **3** | **AI Interviewer (adaptive, 7 types, LLM + bank fallback) · Voice Interview System (STT→engine→TTS, WebSocket room)** | ✅ **Done** |
| **4** | **Coding Interview Platform (pluggable execution: Judge0 prod / local Python dev) · DSA Evaluation Engine (correctness, complexity, quality, readiness)** | ✅ **Done** |
| **5** | **AI Answer Grading (4-dimension rubric + LLM prose) · Behavioral Evaluation (STAR + competencies) · session feedback reports** | ✅ **Done** |
| **6** | **Multi-Agent Workflows — 7 agents over a traced blackboard orchestrator (LangGraph/CrewAI-ready); agent memory + tracing + agent_runs** | ✅ **Done** |
| **7** | **Analytics Dashboard — overview, performance trends (readiness/ATS/coding/communication), skill breakdown, interview history, readiness snapshots** | ✅ **Done** |
| **8** | **Observability — Prometheus /metrics, request tracing + log correlation, error tracking, OTel + Langfuse behind config-gated ports** | ✅ **Done** |
| **9** | **Production Deployment — CI/CD, prod docker-compose (full stack), Kubernetes manifests, Helm chart, Celery worker** | ✅ **Done** |
| **10** | **Enterprise Scaling — multi-tenancy (orgs + mentor dashboard), subscription-tier quotas, caching, read-replica + pool tuning, HA design** | ✅ **Done** |

## Phase 1 — Definition of Done (this delivery)
- [x] Monorepo + backend project scaffold (pyproject, tooling, docker-compose, `.env.example`)
- [x] Core layer: typed settings, async SQLAlchemy engine, Redis, security (Argon2 + JWT)
- [x] DDD Identity context: domain enums/value objects, ORM models, Pydantic schemas
- [x] Repository pattern (interface + SQLAlchemy impl) for users & sessions
- [x] Application services: registration, login, token refresh, RBAC checks
- [x] API v1: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/users/me`, admin user list
- [x] Alembic wired; initial migration for Identity tables
- [x] Tests: `test_auth.py` (register/login/refresh/RBAC) + conftest fixtures
- [x] Health/readiness endpoints, structured logging, exception handlers

## Phase 2 — Definition of Done (delivered)
- [x] Resume context: upload (multipart) → secure validation → PDF/DOCX/TXT parse → disk storage → persist
- [x] Curated skills taxonomy + word-boundary extraction (testable, no LLM)
- [x] Deterministic ATS engine: ATS / recruiter / technical / communication scores + breakdown
- [x] Job context: JD ingestion with auto skill extraction; resume↔JD keyword-gap matching
- [x] ATS optimizer: compatibility %, missing keywords, recruiter insights, LLM rewrite (Ollama default) with offline fallback
- [x] Résumé version control (`resume_versions`, each AI rewrite a new version)
- [x] `LLMProvider` port (Ollama · OpenAI-compatible/vLLM · Stub) — DIP for all future AI
- [x] Migration `0002`; 19 new tests (analyzer unit + API), 32 total green
- [x] Ownership enforcement (cross-user → 404), secure-upload hardening

## Phase 3 — Definition of Done (delivered)
- [x] AI Interviewer: start/answer/state/end; 7 interview types; context-aware questions + follow-ups via `LLMProvider`, curated bank fallback (offline)
- [x] Difficulty adaptation from deterministic answer-signal score; multi-round-ready sessions
- [x] Real-time **WebSocket interview room** (token-auth, streamed Q↔A) + REST flow
- [x] Voice System: STT→engine→TTS pipeline, speaker-attributed transcripts + recordings, replay-ready storage
- [x] STT/TTS ports (`ai/voice`) with stubs; Whisper/Deepgram/ElevenLabs drop-in later
- [x] Migration `0003`; 18 new tests (engine unit, interview API, WS room, voice API), 47 total green
- [x] Ownership enforcement across interview/voice resources; migrations 0001→0003 verified

## Phase 4 — Definition of Done (delivered)
- [x] `ExecutionEngine` port; Judge0 adapter (prod scaffold) + local Python runner (dev/test) + factory
- [x] Explicit code-execution **safety boundary** (gated, sandbox-first, never silently mis-grades)
- [x] Challenge authoring (RBAC: MENTOR/ADMIN), visible + hidden test cases, per-language starter code
- [x] Run (visible) vs Submit (full + persisted) with real Python execution
- [x] DSA evaluation: correctness, edge-case, code-quality, time/space complexity, readiness, difficulty, suggestions
- [x] Migration `0004`; 16 new tests (complexity unit + execution/eval API), 63 total green
- [x] Hidden-case non-leakage; owner-only submissions; migrations 0001→0004 verified

## Phase 5 — Definition of Done (delivered)
- [x] AI Answer Grading: 4-dimension rubric (technical/communication/completeness/confidence), score /10, feedback
- [x] LLM prose behind the port: suggested better answer, industry-standard answer, recruiter perspective (deterministic fallbacks)
- [x] Behavioral analyzer: STAR detector + competencies (leadership/ownership/teamwork/problem-solving), recruiter view
- [x] Ethics guardrail — judge content/delivery only, never protected characteristics or hiring decisions
- [x] Session feedback reports: grade every answered turn, aggregate strengths/improvements, persist `FeedbackReport`
- [x] Polymorphic `scores` table feeding Phase-7 analytics; migration `0005`
- [x] 17 new tests (rubric/STAR unit + evaluation API + session report), 76 total green; migrations 0001→0005 verified

## Phase 6 — Definition of Done (delivered)
- [x] 7 agents (Resume, ATS, Interviewer, Coding Evaluator, Behavioral, Feedback, Career Coach) wrapping earlier-phase engines
- [x] Blackboard + DAG orchestrator: ordered run, input-driven skipping, failure isolation, full step tracing
- [x] Agent memory (short-term scratch + long-term persisted runs) and `Tracer` port (Langfuse-ready)
- [x] `Agent` interface as the LangGraph/CrewAI swap-in seam (documented)
- [x] `career-readiness` workflow API; `agent_runs` persistence (metadata-only inputs, full trace); migration `0006`
- [x] 10 new tests (orchestrator/agents unit + workflow API), 86 total green; migrations 0001→0006 verified

## Phase 7 — Definition of Done (delivered)
- [x] Dashboard overview: totals + composite readiness + coding/ATS/interview stats + dimension breakdown
- [x] Performance trends (readiness/ATS/coding/communication/technical), day & week buckets, with summaries
- [x] Interview history + recent activity per kind; ATS improvement delta; coding acceptance/readiness
- [x] Pure, DB-free aggregation helpers (portable Postgres/SQLite, unit-tested)
- [x] `metric_snapshots` for readiness-over-time (capture endpoint; Celery-ready); migration `0007`
- [x] Per-user scoping on every query (ats_reports via resume-ownership join)
- [x] 11 new tests (aggregation unit + analytics integration), 97 total green; migrations 0001→0007 verified

## Phase 8 — Definition of Done (delivered)
- [x] In-house Prometheus metrics (Counter/Gauge/Histogram) + `GET /metrics` exposition
- [x] HTTP metrics (requests/latency/in-flight), `app_errors_total`, `agent_runs_total` (route-template labels)
- [x] Request tracing: W3C trace id + request id, propagation, response headers
- [x] Structured-log correlation (trace/request id bound to structlog context — Loki-ready)
- [x] Unhandled-exception handler: logs + counts + safe 500 (no leak)
- [x] OpenTelemetry hook (lazy) + Langfuse agent-trace export behind the Phase-6 Tracer port
- [x] 9 new tests (metrics unit + observability integration), 106 total green

## Phase 9 — Definition of Done (delivered)
- [x] GitHub Actions CI/CD: ruff lint → pytest → Docker Buildx build & push to GHCR (sha + latest)
- [x] Ruff config tuned to clean (ast-visitor N815 + str-Enum UP042 exemptions); **lint passes**
- [x] Celery worker app + tasks (async offload surface) + beat schedule example
- [x] `infra/docker-compose.prod.yml`: API + worker + Postgres + Redis + Judge0 + Prometheus + Grafana + Loki
- [x] Prometheus scrape / Grafana datasource / Loki configs
- [x] Kubernetes manifests: namespace, config/secret, Postgres/Redis, migration Job, backend+worker, HPA, TLS Ingress
- [x] Helm chart (`infra/helm/prepforge`) with pre-upgrade migration hook, HPA/ingress/worker flags
- [x] Migrations run as a discrete step (Job/hook), never in app startup; all YAML validated; 106 tests green

## Phase 10 — Definition of Done (delivered)
- [x] Multi-tenancy: Organizations + memberships (owner/admin/mentor/member), migration `0008`
- [x] Mentor dashboard — org-level readiness rollup reusing the analytics engine; role-based authz
- [x] Subscription-tier quotas (per-plan daily limits) with pluggable Redis/in-memory counter store; enforced on agent workflow (429)
- [x] Cache port (Redis + in-memory) caching the analytics overview
- [x] Connection-pool tuning + read-replica engine/dependency (mentor dashboard reads the replica; writes stay primary)
- [x] HA + partitioning strategy documented; 18 new tests, 120 total green; migrations 0001→0008 verified; ruff clean

> **Backend complete (Phases 1–10).** Optional next: Next.js frontend (dashboard, interview/coding rooms, analytics charts) consuming these APIs.

## Conventions going forward
- Branch per phase; PR with migration + tests; CI must be green.
- New tables only via Alembic; never edit a shipped migration.
- New LLM features go behind the `LLMProvider` port (Ollama default).
- Public API changes are versioned (`/api/v1`, `/api/v2`).
