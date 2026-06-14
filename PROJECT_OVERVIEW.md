# PrepForge — AI Interview Preparation Platform · Project Overview

A complete, production-style platform that helps candidates prepare for technical and
behavioral interviews with AI: an adaptive AI interviewer (text + voice), résumé & ATS
analysis, a LeetCode-style coding room with automatic DSA evaluation, answer grading,
a multi-agent "career readiness" workflow, analytics dashboards, teams/mentor mode,
and full observability.

This document explains **what every file does** and **which technologies are used**, so a
new contributor can understand the whole system without opening the code.

---

## 1. Run it in one click

| Action | File | What happens |
|---|---|---|
| **Start** | `Start_PrepForge.bat` | Creates the Python venv + installs deps (first run), writes a local SQLite `.env`, runs DB migrations, starts the **backend** and **frontend**, and opens the browser. |
| **Stop** | `Stop_PrepForge.bat` | Stops the backend and frontend windows and frees the ports. |

- **Web app:** http://localhost:3077
- **API + interactive docs (Swagger):** http://localhost:8077/docs
- No Docker, Postgres, or Redis needed for local use — it runs on **SQLite** and degrades
  gracefully when Redis/Ollama are absent.
- Optional: install [Ollama](https://ollama.com) and run `ollama serve` for richer, dynamic
  AI responses. Without it, the app uses fast built-in deterministic fallbacks.

---

## 2. Technology stack

### Backend
| Technology | Why it's used |
|---|---|
| **Python 3.12** | Backend language. |
| **FastAPI** | Async web framework — REST + WebSocket APIs, automatic OpenAPI docs. |
| **Uvicorn** | ASGI server that runs the app. |
| **SQLAlchemy 2.0 (async)** | ORM / database toolkit (async engine + sessions). |
| **Alembic** | Versioned, reversible database migrations. |
| **Pydantic v2 / pydantic-settings** | Request/response validation (DTOs) and typed config. |
| **PostgreSQL (prod) / SQLite (dev & tests)** | Relational database; pgvector-ready for embeddings. |
| **Redis** | Caching, rate limiting, quotas, Celery broker (optional locally). |
| **Celery** | Background/async jobs (parsing, embeddings, reports). |
| **Argon2 (argon2-cffi)** | Secure password hashing. |
| **PyJWT** | JWT access/refresh tokens. |
| **structlog** | Structured (JSON) logging with request/trace correlation. |
| **pypdf / python-docx** | Parse PDF and DOCX résumés. |
| **httpx** | Async HTTP client (LLM/Judge0 calls, tests). |
| **pytest** | Test suite (121 tests, runs on in-memory SQLite). |
| **ruff** | Linter / formatter. |

### AI / ML layer (all behind swappable "ports")
| Technology | Why it's used |
|---|---|
| **LLM provider port** | Ollama (local default), OpenAI-compatible, or vLLM — selected by config. Every AI feature has a deterministic fallback so it works offline. |
| **Speech ports (STT/TTS)** | Whisper / Faster-Whisper / Deepgram (speech-to-text) and ElevenLabs / Piper (text-to-speech) drop in behind a stub. |
| **Execution engine port** | Judge0 / Docker sandbox in production; a local Python runner for dev/tests. |
| **Multi-agent orchestrator** | In-house blackboard/DAG runner; LangGraph / CrewAI can replace it behind the same interface. |
| **Langfuse / OpenTelemetry** | LLM tracing + distributed tracing (config-gated). |

### Frontend
| Technology | Why it's used |
|---|---|
| **Next.js 14 (App Router)** | React framework, routing, dev server + API proxy. |
| **React 18 + TypeScript** | UI library + type safety. |
| **TailwindCSS** | Utility-first styling (dark-mode-first design). |
| **Zustand** | Lightweight client state (auth tokens/user), persisted to localStorage. |
| **TanStack React Query** | Server-state fetching/caching. |
| **Axios** | HTTP client with automatic JWT attach + token refresh. |
| **Monaco Editor** | The in-browser code editor (the engine behind VS Code) for the Coding Room. |
| **Recharts** | Analytics charts. |
| **lucide-react** | Icon set. |

### Infrastructure / DevOps
Docker & Docker Compose · Kubernetes manifests · Helm chart · GitHub Actions CI/CD ·
Prometheus (metrics) · Grafana (dashboards) · Loki (logs) · Judge0 (code sandbox).

---

## 3. Architecture in one picture

```
Browser (Next.js, :3077)
   |  HTTP / WebSocket  (Next dev proxies /api -> backend)
   v
FastAPI backend (:8077)
   API layer (routers + auth/RBAC dependencies)
        | calls
   Services layer (use-cases: orchestrate everything)
        | uses
   +--------------+----------------+---------------------+
   Domain logic    Repositories      AI ports
   (pure, tested)  (DB access)       (LLM / speech / code-exec / agents)
        |               |                    |
        v               v                    v
   business rules    PostgreSQL/SQLite    Ollama / Judge0 / Langfuse ...
```

**Design principles:** Clean Architecture (dependencies point inward), Domain-Driven
Design (one module per business area), SOLID (services depend on interfaces/ports, not
concrete vendors). The **domain layer is pure** (no framework imports) so it's fast and
fully unit-testable; vendors (LLMs, sandboxes) sit behind ports and are swappable.

**Typical request flow:** `router -> dependency (verify JWT + role) -> service (use-case) ->
repository (DB) and/or AI port -> response DTO`.

---

## 4. Repository layout (top level)

```
AI_Interview_Preperation_Project/
├── Start_PrepForge.bat / Stop_PrepForge.bat   one-click run / stop (Windows)
├── README.md / PROJECT_OVERVIEW.md            docs
├── docker-compose.yml                         dev infra (Postgres + Redis + backend)
├── .env.example                               sample environment config
├── backend/                                   FastAPI service + Celery worker
├── frontend/                                  Next.js web app
├── infra/                                     prod compose, Kubernetes, Helm, monitoring
└── docs/                                      architecture, schema, per-module docs
```

---

## 5. Backend — file by file

Path root: `backend/app/`

### `main.py` & startup
| File | What it does |
|---|---|
| `main.py` | **Composition root.** Builds the FastAPI app, registers middleware (CORS, security headers, rate limiting, observability), mounts routers, sets exception handlers, and on startup seeds roles + sample coding challenges. |
| `bootstrap.py` | Idempotent startup seeding: creates the RBAC **roles** and **5 public starter coding challenges** (two-sum, reverse-string, fizzbuzz, valid-palindrome, maximum-subarray) if the DB is empty. |

### `core/` — cross-cutting infrastructure
| File | What it does |
|---|---|
| `config.py` | Typed settings loaded from environment / `.env` (DB URL, secrets, ports, feature flags, LLM/observability config). |
| `database.py` | Async SQLAlchemy engine + session factories, the ORM `Base`, connection-pool tuning, and a read-replica session (`get_read_db`). |
| `security.py` | Password hashing (Argon2id) and JWT create/verify for access + refresh tokens. |
| `redis.py` | Shared async Redis client (fast-fail so it never hangs when Redis is down). |
| `cache.py` | Cache abstraction: in-memory (dev) or Redis (prod); used to cache analytics. |
| `middleware.py` | Security-headers middleware + Redis sliding-window rate limiter (fails open). |
| `observability.py` | Request middleware: assigns a trace id + request id, records HTTP metrics, correlates logs; optional OpenTelemetry hook. |
| `metrics.py` | Dependency-free Prometheus metrics (Counter/Gauge/Histogram) + `/metrics` text format. |
| `logging.py` | structlog configuration (JSON in prod, pretty in dev). |
| `exceptions.py` | App error hierarchy (NotFound, Conflict, AuthError…) + handlers that map them to clean JSON; tracks unhandled errors. |

### `domain/` — pure business logic (no framework, fully tested)
| File | What it does |
|---|---|
| `identity/enums.py` | Roles (ADMIN/MENTOR/RECRUITER/USER), subscription plans, experience levels, OAuth providers. |
| `resume/skills.py` | Curated **skills taxonomy** + extractor that finds canonical skills (Python, FastAPI, Docker…) in text. |
| `resume/analyzer.py` | **Deterministic ATS scoring engine** — computes ATS, recruiter, technical, communication scores + keyword gaps from résumé text. |
| `resume/enums.py` | Résumé statuses, file types, and section keywords. |
| `interview/enums.py` | Interview types (HR, technical, system design, ML, GenAI, DevOps, PM), difficulty, statuses, turn roles. |
| `interview/questions.py` | **Large question bank**: general questions per interview type + `SKILL_QUESTIONS` (technology-specific questions for ~30 skills) used to tailor interviews to a résumé. |
| `interview/scoring.py` | Deterministic answer-signal scorer that drives live difficulty adaptation. |
| `evaluation/rubric.py` | 4-dimension answer rubric (technical/communication/completeness/confidence). |
| `evaluation/star.py` | STAR-method detector (Situation/Task/Action/Result) for behavioral answers. |
| `evaluation/grader.py` | Combines rubric + STAR into answer & behavioral grades with feedback. |
| `evaluation/enums.py` | Grading dimensions, behavioral competencies, subject types. |
| `coding/complexity.py` | Static **time/space complexity estimator** (Python AST + regex heuristics). |
| `coding/quality.py` | Static **code-quality scorer** (length, nesting, docstrings, bare excepts…). |
| `coding/evaluator.py` | Combines test results + complexity + quality into a DSA evaluation (correctness, readiness, suggestions). |
| `coding/enums.py` | Languages, difficulties, submission statuses, complexity classes. |
| `agents/enums.py` | Agent names, run/step statuses, and a role->interview-type mapping. |
| `analytics/aggregations.py` | Pure trend-bucketing + summary helpers (portable across DBs). |
| `analytics/enums.py` | Metric names, time buckets, history kinds. |
| `billing/plans.py` | Subscription-tier quota limits per feature (free/pro/team/enterprise). |
| `organization/enums.py` | Organization roles and plans. |

### `models/` — database tables (SQLAlchemy ORM)
| File | Tables it defines |
|---|---|
| `user.py` | `users`, `roles`, `user_roles`, `oauth_accounts`, `sessions`, `subscriptions`, `audit_logs` (+ shared JSON type & enum helper). |
| `resume.py` | `resumes`, `resume_versions`, `job_descriptions`, `ats_reports`. |
| `interview.py` | `interviews`, `interview_sessions`, `turns`, `voice_sessions`, `transcripts`, `recordings`. |
| `coding.py` | `coding_challenges`, `test_cases`, `coding_submissions`. |
| `evaluation.py` | `scores` (polymorphic), `feedback_reports`. |
| `agent.py` | `agent_runs` (multi-agent workflow runs + traces). |
| `analytics.py` | `metric_snapshots` (readiness captured over time). |
| `organization.py` | `organizations`, `organization_memberships`. |

### `schemas/` — API contracts (Pydantic DTOs)
One file per area defines the JSON request/response shapes (never expose ORM objects):
`auth.py`, `user.py`, `resume.py`, `interview.py`, `coding.py`, `evaluation.py`,
`agent.py`, `analytics.py`, `organization.py`.

### `repositories/` — data access (one job: talk to the DB)
| File | What it does |
|---|---|
| `base.py` | Repository Protocol (interface) for Dependency Inversion. |
| `user.py` / `session.py` | Users & roles; refresh-token sessions (rotation/revocation). |
| `resume.py` | Résumés, résumé versions, job descriptions, ATS reports. |
| `interview.py` | Interviews/sessions/turns + voice sessions/transcripts/recordings. |
| `coding.py` | Challenges, test cases, submissions. |
| `evaluation.py` | Scores and feedback reports. |
| `agent.py` | Agent runs. |
| `analytics.py` | Cross-table read queries + metric snapshots. |
| `organization.py` | Orgs and memberships. |

### `services/` — use-cases (orchestrate domain + repositories + AI)
| File | What it does |
|---|---|
| `auth_service.py` | Register, login, JWT issue, refresh-token rotation, logout. |
| `resume_service.py` | Résumé upload->parse->store; JD creation; ATS analyze & AI-optimize. |
| `interview_service.py` | Start/answer/end interviews; difficulty adaptation; **pulls skills from your résumé** to tailor questions. |
| `voice_service.py` | Voice interview pipeline: speech->text -> interview engine -> text->speech; stores transcripts/recordings. |
| `coding_service.py` | Challenge authoring; run (visible tests) / submit (all tests) + DSA evaluation. |
| `evaluation_service.py` | AI answer grading, behavioral evaluation, and whole-session feedback reports. |
| `agent_service.py` | Runs the 7-agent career-readiness workflow; persists run + trace; emits metrics. |
| `analytics_service.py` | Dashboard overview, trends, history, snapshots (cached, read-replica aware). |
| `organization_service.py` | Create org, manage members, mentor readiness dashboard. |
| `quota_service.py` | Per-plan daily usage quotas (fails open if Redis is down). |
| `storage.py` | File storage port + local-disk implementation (S3/MinIO later). |
| `parsing/document_parser.py` | Secure PDF/DOCX/TXT text extraction (extension + magic-byte + size validation). |

### `ai/` — AI ports & engines (vendor-agnostic)
| File | What it does |
|---|---|
| `llm/base.py` | `LLMProvider` interface (chat). |
| `llm/providers.py` | Ollama / OpenAI-compatible / vLLM providers + a deterministic Stub + factory. |
| `interview_engine.py` | Generates the next interview question (LLM when available, **skill-aware question bank** fallback) + interview summaries. |
| `grading.py` | LLM helpers for "better answer", "industry-standard answer", recruiter perspective (with offline fallbacks). |
| `voice/base.py` / `voice/providers.py` | Speech-to-text & text-to-speech ports + offline stubs. |
| `execution/base.py` | `ExecutionEngine` interface + request/result types. |
| `execution/local_python.py` | Runs submitted Python in a timed subprocess (dev/test; **not** a sandbox). |
| `execution/judge0.py` | Judge0 sandbox adapter for production multi-language execution. |
| `execution/factory.py` | Picks Judge0 if configured, else the local runner. |
| `agents/base.py` | Agent interface + `AgentContext` (shared blackboard) + the orchestrator (runs agents, skips when inputs missing, traces each step). |
| `agents/agents.py` | The **7 agents**: Resume, ATS, Interviewer, Coding-Evaluator, Behavioral, Feedback, Career-Coach (each reuses the domain engines). |
| `agents/tracing.py` | Tracer port + in-memory tracer + Langfuse export hook. |

### `api/v1/` — HTTP transport
| File | What it does |
|---|---|
| `router.py` | Aggregates all endpoint routers under `/api/v1`. |
| `deps.py` | Reusable dependencies: DB sessions, `get_current_user`, `require_roles` (RBAC), quota guard, and wiring of every service. |
| `endpoints/auth.py` | `POST /auth/register|login|refresh|logout`. |
| `endpoints/users.py` | `GET/PATCH /users/me`, admin user list. |
| `endpoints/resume.py` | Upload/list résumés, analyze (ATS), create JD, optimize résumé. |
| `endpoints/interview.py` | Start/answer/end interview, list turns, **WebSocket** live interview room. |
| `endpoints/voice.py` | Start a voice session, upload an audio turn, fetch transcript. |
| `endpoints/coding.py` | List/get challenges, author challenge (mentor/admin), run/submit code, get submission. |
| `endpoints/evaluation.py` | Grade an answer, grade a behavioral answer, grade a whole session, list scores. |
| `endpoints/agents.py` | List agents, run career-readiness workflow, list/get runs (quota-guarded). |
| `endpoints/analytics.py` | Dashboard overview, trends, history, capture snapshot. |
| `endpoints/organizations.py` | Create/list orgs, manage members, mentor dashboard. |
| `endpoints/health.py` | `/health` (liveness) and `/ready` (readiness) probes. |
| `endpoints/observability.py` | `/metrics` Prometheus exposition. |

### `worker/` — background processing
| File | What it does |
|---|---|
| `celery_app.py` | Celery application (Redis broker) + beat schedule for periodic jobs. |
| `tasks.py` | Async tasks (e.g., `ping`, daily readiness-snapshot capture). |

### `alembic/versions/` — database migrations (run in order)
`0001_initial_identity` (users/roles/sessions) -> `0002_resume_ats` -> `0003_interview_voice`
-> `0004_coding` -> `0005_evaluation` -> `0006_agents` -> `0007_analytics` -> `0008_organizations`.

### `tests/` — automated tests (pytest, in-memory SQLite, 121 tests)
`conftest.py` provides fixtures (test DB, HTTP client, auth headers). Test files mirror the
features: `test_auth`, `test_resume`, `test_analyzer`, `test_interview`,
`test_interview_engine`, `test_voice`, `test_coding`, `test_complexity`, `test_grading`,
`test_evaluation_api`, `test_agents`, `test_agents_api`, `test_aggregations`,
`test_analytics_api`, `test_cache`, `test_quota`, `test_metrics`,
`test_observability_api`, `test_organizations`.

---

## 6. Frontend — file by file

Path root: `frontend/src/`

### App routes (`app/`)
| File | What it does |
|---|---|
| `layout.tsx` | Root layout: fonts, dark theme, global providers. |
| `providers.tsx` | Wraps the app in the React Query client. |
| `page.tsx` | Landing route — redirects to `/dashboard` or `/login` based on auth. |
| `globals.css` | Tailwind base + design tokens (colors, dark mode, animations). |
| `(auth)/layout.tsx` | Split-screen branding layout for auth pages. |
| `(auth)/login/page.tsx` | Login form (-> `/auth/login`). |
| `(auth)/register/page.tsx` | Registration form (-> `/auth/register`). |
| `(app)/layout.tsx` | Protected app shell — route guard + sidebar + topbar. |
| `(app)/dashboard/page.tsx` | Readiness gauge, stat cards, answer-quality breakdown (`/analytics/overview`). |
| `(app)/resume/page.tsx` | Drag-to-upload résumés (PDF/DOCX/TXT) + parsed list. |
| `(app)/ats/page.tsx` | ATS Optimizer: résumé × job description -> scores + AI-rewritten résumé. |
| `(app)/interview/page.tsx` | Interview Room: adaptive Q&A in **text or voice**; choose count + focus skills. |
| `(app)/coding/page.tsx` | Coding Room challenge list. |
| `(app)/coding/[id]/page.tsx` | Challenge detail: **Monaco editor** + Run/Submit + DSA results panel. |
| `(app)/analytics/page.tsx` | Trend charts (Recharts) + interview history. |
| `(app)/learning/page.tsx` | Runs the 7-agent career-readiness workflow -> readiness, plan, practice questions. |
| `(app)/teams/page.tsx` | Create org, manage members, mentor readiness dashboard. |
| `(app)/settings/page.tsx` | View/update profile. |

### Components & libraries
| File | What it does |
|---|---|
| `components/sidebar.tsx` | Left navigation with the 9 sections. |
| `components/topbar.tsx` | Top bar: plan badge, theme toggle, avatar, logout. |
| `components/theme-toggle.tsx` | Light/dark mode switch. |
| `components/page-header.tsx` | Reusable page title/description. |
| `components/coming-soon.tsx` | Placeholder card. |
| `components/voice-recorder.tsx` | Microphone recorder (MediaRecorder) for voice interviews. |
| `components/ui/button.tsx · card.tsx · input.tsx · misc.tsx` | shadcn-style UI primitives (button, card, input, label/badge/skeleton/progress). |
| `lib/api.ts` | Axios client: attaches JWT, auto-refreshes on 401, maps API errors. |
| `lib/auth-store.ts` | Zustand store for user + tokens, persisted to localStorage. |
| `lib/hooks.ts` | React Query hooks (login, register, me, overview, trends, resumes, challenges, orgs, history). |
| `lib/types.ts` | TypeScript types mirroring the backend DTOs. |
| `lib/utils.ts` | Helpers (`cn` class merge, score colors, initials). |

### Frontend config
`package.json` (deps/scripts), `next.config.mjs` (dev `/api` -> backend proxy),
`tailwind.config.ts`, `tsconfig.json`, `.eslintrc.json`, `.env.local.example`.

---

## 7. Infrastructure (`infra/`) & CI

| Path | What it does |
|---|---|
| `docker-compose.prod.yml` | Full prod-like stack: backend + worker + Postgres + Redis + Judge0 + Prometheus + Grafana + Loki. |
| `prometheus/prometheus.yml` | Scrape config for the backend `/metrics`. |
| `grafana/provisioning/datasources/datasources.yml` | Wires Prometheus + Loki into Grafana. |
| `loki/loki.yml` | Log-aggregation config. |
| `k8s/00..50*.yaml` | Kubernetes manifests: namespace, config/secrets, Postgres, Redis, migration job, backend+worker deployments, HPA + TLS ingress. |
| `helm/prepforge/` | Helm chart (templated config/secrets, deployments, HPA, ingress, pre-upgrade migration hook). |
| `.github/workflows/ci.yml` | CI/CD: ruff lint -> pytest -> build & push Docker image. |

---

## 8. Database tables (summary)

**Identity:** users, roles, user_roles, oauth_accounts, sessions, subscriptions, audit_logs ·
**Résumé/Job:** resumes, resume_versions, job_descriptions, ats_reports ·
**Interview/Voice:** interviews, interview_sessions, turns, voice_sessions, transcripts, recordings ·
**Coding:** coding_challenges, test_cases, coding_submissions ·
**Evaluation:** scores, feedback_reports ·
**Agents:** agent_runs · **Analytics:** metric_snapshots · **Teams:** organizations, organization_memberships.

Full column-level detail: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

---

## 9. Feature → where it lives (quick map)

| Feature | Backend | Frontend |
|---|---|---|
| Auth & profiles | `services/auth_service.py`, `endpoints/auth.py`,`users.py` | `(auth)/*`, `settings` |
| Résumé analysis | `domain/resume/analyzer.py`, `services/resume_service.py` | `resume` |
| ATS optimization | `resume_service.py` + LLM rewrite | `ats` |
| AI interviewer | `ai/interview_engine.py`, `services/interview_service.py` | `interview` |
| Voice interview | `services/voice_service.py`, `ai/voice/*` | `interview` (voice) + `voice-recorder` |
| Coding + DSA eval | `ai/execution/*`, `domain/coding/*`, `services/coding_service.py` | `coding`, `coding/[id]` |
| Answer/behavioral grading | `domain/evaluation/*`, `services/evaluation_service.py` | (used by interview/learning) |
| Multi-agent workflow | `ai/agents/*`, `services/agent_service.py` | `learning` |
| Analytics | `domain/analytics/*`, `services/analytics_service.py` | `dashboard`, `analytics` |
| Teams / mentor | `services/organization_service.py` | `teams` |
| Observability | `core/metrics.py`, `core/observability.py` | — |

---

## 10. How to test it

1. **Backend tests:** `cd backend && .venv\Scripts\python.exe -m pytest -q` → 121 passing.
2. **Frontend checks:** `cd frontend && npm run typecheck && npm run lint && npm run build`.
3. **Manual:** run `Start_PrepForge.bat`, register, then walk the sidebar — upload a résumé,
   run an interview, solve a coding challenge, generate a learning plan, view analytics.
4. **API:** open http://localhost:8077/docs, register, Authorize with the token, call endpoints.

More detail: [README.md](README.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/ROADMAP.md](docs/ROADMAP.md) and the
per-module docs in [docs/modules/](docs/modules/).
