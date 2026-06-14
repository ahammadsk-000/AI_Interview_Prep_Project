# PrepForge — AI Interview Preparation Platform · Architecture

> Enterprise-grade, production-ready platform for AI-driven interview preparation.
> Clean Architecture · DDD · SOLID · modular monorepo evolving into deployable microservices.

---

## 1. High-Level Architecture

```
                                   ┌─────────────────────────────────────────────┐
                                   │                  CLIENTS                      │
                                   │  Next.js Web App · Mobile (future) · API SDK  │
                                   └───────────────┬───────────────────────────────┘
                                                   │ HTTPS / WSS
                                   ┌───────────────▼───────────────┐
                                   │      API Gateway / Ingress     │
                                   │  (NGINX / Traefik · TLS · WAF) │
                                   └───────────────┬───────────────┘
                                                   │
            ┌──────────────────────────────────────┼──────────────────────────────────────┐
            │                                       │                                       │
   ┌────────▼─────────┐                  ┌──────────▼──────────┐                ┌───────────▼──────────┐
   │   FastAPI App    │                  │   WebSocket Gateway  │               │   Voice Gateway      │
   │  (REST · v1 API) │                  │ (interview · coding) │               │ (WebRTC · STT · TTS) │
   └────────┬─────────┘                  └──────────┬──────────┘                └───────────┬──────────┘
            │                                       │                                       │
            └───────────────────────┬───────────────┴───────────────────────┬───────────────┘
                                    │                                       │
                       ┌────────────▼────────────┐            ┌─────────────▼──────────────┐
                       │   Application Services    │            │   Celery Workers           │
                       │  (use-cases / orchestr.)  │            │  (async: parsing, grading, │
                       │                           │            │   report gen, embeddings)  │
                       └────────────┬──────────────┘            └─────────────┬──────────────┘
                                    │                                          │
        ┌───────────────────────────┼──────────────────────────────────────────┼──────────────────┐
        │                           │                                          │                  │
┌───────▼────────┐      ┌───────────▼──────────┐    ┌──────────────────────────▼───┐   ┌──────────▼─────────┐
│  AI Orchestr.  │      │   Domain Services    │    │      Infrastructure          │   │   Code Execution   │
│ LangGraph ·    │      │  (pure business      │    │  PostgreSQL · Redis ·        │   │  Judge0 · Docker   │
│ CrewAI agents  │      │   logic, DDD)        │    │  pgvector · S3/MinIO ·        │   │  sandboxes         │
│                │      │                      │    │  Object storage              │   │                    │
└───────┬────────┘      └──────────────────────┘    └──────────────────────────────┘   └────────────────────┘
        │
┌───────▼─────────────────────────────────────────────┐
│   LLM / Model Layer                                   │
│   Ollama (default, local) · vLLM · OpenAI-compatible  │
│   Whisper / Faster-Whisper (STT) · ElevenLabs (TTS)   │
│   SentenceTransformers (embeddings)                   │
└───────────────────────────────────────────────────────┘

   Cross-cutting:  OpenTelemetry · Prometheus/Grafana · Loki · Langfuse (LLM tracing) · Audit log
```

### Design tenets
- **Clean Architecture**: dependencies point inward. `api → services → domain ← repositories → infrastructure`. The domain has zero framework imports.
- **DDD**: bounded contexts map to modules (Identity, Resume, Interview, Coding, Evaluation, Analytics, Learning). Each context owns its aggregates, value objects, and repository interfaces.
- **SOLID**: services depend on repository *interfaces* (DIP); LLM providers behind a `LLMProvider` port (OCP); single-responsibility use-case classes.
- **Modular monolith → microservices**: ships as one deployable backend, but module boundaries are clean enough to extract `voice`, `coding-exec`, and `ai-orchestrator` into separate services under load.

---

## 2. Bounded Contexts (DDD)

| Context | Aggregates | Responsibility |
|---|---|---|
| **Identity & Access** | User, Role, Subscription, Session | Auth, RBAC, OAuth, profiles, plans |
| **Resume** | Resume, ResumeVersion, AtsReport | Upload, parse, score, optimize |
| **Job** | JobDescription, SkillMap | JD ingestion, keyword extraction |
| **Interview** | Interview, InterviewSession, Turn | AI interviewer, multi-round flow |
| **Voice** | VoiceSession, Transcript, Recording | Realtime STT/TTS, replay |
| **Coding** | Challenge, Submission, TestCase | LeetCode-style execution + DSA eval |
| **Evaluation** | Score, Rubric, Feedback, AgentRun | Answer grading, behavioral, multi-agent |
| **Analytics** | MetricSnapshot, Trend | Dashboards, readiness scoring |
| **Learning** | LearningPlan, Roadmap, Milestone | Personalized study paths |

---

## 3. Backend Architecture (layered)

```
backend/app/
├── core/            # config, security, db, redis, logging, telemetry (cross-cutting)
├── domain/          # entities, value objects, enums, domain services (NO framework deps)
│   └── <context>/
├── models/          # SQLAlchemy ORM (persistence representation)
├── schemas/         # Pydantic v2 DTOs (API contracts)
├── repositories/    # interfaces + SQLAlchemy implementations (data access)
├── services/        # application/use-case layer (orchestrates domain + infra)
├── api/v1/          # FastAPI routers + dependencies (transport layer)
├── ai/              # LLM ports, providers, agent graphs (LangGraph/CrewAI)
├── workers/         # Celery tasks
└── main.py          # composition root / DI wiring
```

**Request flow**: `router → dependency (auth/RBAC) → service (use-case) → repository (port) → SQLAlchemy → Postgres`. DTOs cross the API boundary; ORM models never leak to clients.

---

## 4. AI Architecture

- **Provider port** (`ai/llm/base.py`): `LLMProvider` interface with `chat`, `stream`, `embed`. Implementations: `OllamaProvider` (default), `OpenAICompatibleProvider`, `VLLMProvider`. Selected via config — no hard dependency on any vendor.
- **Multi-agent (Module 11)**: LangGraph state machine orchestrating CrewAI agents (Interviewer, Resume, ATS, Coding Evaluator, Behavioral, Feedback, Career Coach). Shared agent memory in Redis + Postgres; every run traced to Langfuse and persisted as an `AgentRun` aggregate.
- **RAG**: pgvector + SentenceTransformers for company/role-specific question banks and resume↔JD matching.
- **Grading**: rubric-driven LLM-as-judge with structured output (Pydantic-validated) → deterministic `Score` value objects.

---

## 5. Infrastructure Architecture

| Concern | Dev | Production |
|---|---|---|
| Compute | docker-compose | Kubernetes + Helm |
| DB | Postgres container | Managed Postgres (HA, read replicas) + pgvector |
| Cache/Broker | Redis container | Redis cluster / managed |
| Object store | MinIO | S3-compatible |
| Async | Celery + Redis | Celery workers (HPA) + flower |
| Code exec | Judge0 + Docker | Isolated node pool, gVisor/Firecracker sandbox |
| LLM | Ollama local | vLLM on GPU node pool / managed API |
| Observability | Prometheus, Grafana, Loki, Langfuse | same, federated |
| Secrets | `.env` | External Secrets Operator / Vault |

---

## 6. Security Architecture

- **AuthN**: JWT (short-lived access + rotating refresh, stored hashed), OAuth2 (Google, GitHub), Argon2id password hashing.
- **AuthZ**: RBAC (`ADMIN`, `MENTOR`, `RECRUITER`, `USER`) enforced via FastAPI dependencies; resource-ownership checks in services.
- **Hardening**: rate limiting (Redis sliding window), strict CORS, security headers, request-size limits, secure file upload (MIME sniffing + size + AV hook + sandboxed parse), audit logging of sensitive actions, secrets via env/Vault, no PII in logs.
- **Module 10 ethics guardrail**: presentation-signal analysis only; never infers protected characteristics or makes hiring decisions.

---

## 7. Scalability

- Stateless API replicas behind LB; sessions/state in Redis + Postgres.
- Heavy work (parsing, embeddings, grading, report gen, voice transcoding) offloaded to Celery → horizontal worker scaling.
- Code execution isolated on a dedicated, autoscaled node pool.
- LLM inference scales independently (vLLM replicas / batching).
- DB: connection pooling (pgbouncer), read replicas for analytics, partitioning for high-volume tables (submissions, turns, metrics).

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) and [ROADMAP.md](ROADMAP.md).
