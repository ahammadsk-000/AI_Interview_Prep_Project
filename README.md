# PrepForge — AI Interview Preparation Platform

Enterprise-grade, production-ready platform for AI-driven interview preparation: AI interviewer, resume/ATS analysis, voice & coding interviews, multi-agent evaluation, analytics, and personalized learning paths.

- **Backend**: FastAPI · Python 3.12 · PostgreSQL · Redis · SQLAlchemy (async) · Alembic · Celery
- **AI**: LangGraph · CrewAI · LangChain · Ollama (default) · vLLM · SentenceTransformers
- **Frontend**: Next.js (App Router) · TypeScript · TailwindCSS · Zustand · React Query — see [frontend/README.md](frontend/README.md)

> Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Schema: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) · Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

## Repository layout
```
.
├── docs/            # architecture, schema, roadmap, per-module + deployment docs
├── backend/         # FastAPI service + Celery worker (Phases 1–8)
├── frontend/        # Next.js app (scaffolded in a later phase)
├── infra/           # docker-compose.prod, k8s manifests, Helm chart, observability configs
├── .github/workflows/   # CI/CD (lint → test → build/push)
└── docker-compose.yml   # dev stack (Postgres + Redis + backend)
```

## Deployment
Dev: `docker compose up`. Full prod-like stack (API + worker + Postgres + Redis + Judge0 +
Prometheus/Grafana/Loki): `docker compose -f infra/docker-compose.prod.yml --env-file .env up -d`.
Kubernetes via raw manifests (`infra/k8s/`) or the Helm chart (`infra/helm/prepforge/`).
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Quickstart (backend, Phase 1)
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp ../.env.example ../.env                          # then edit secrets
# bring up Postgres + Redis
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

## Test
```bash
cd backend
pytest -q
```

Phase 1 status: **Auth & User Management** — JWT (access + refresh), RBAC, OAuth scaffolding, sessions, subscriptions. See the roadmap for what's next.
