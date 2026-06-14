# Deployment (Phase 9)

Production-deployment artifacts for PrepForge. Status: **implemented**.

## Layout
```
.github/workflows/ci.yml          CI/CD: lint → test → build & push image
backend/Dockerfile                Multi-stage, non-root, healthcheck
backend/app/worker/               Celery app + tasks (async offload)
docker-compose.yml                Dev: Postgres + Redis + backend
infra/
├── docker-compose.prod.yml       Full prod-like stack (below)
├── prometheus/prometheus.yml     Scrape config (backend /metrics)
├── grafana/provisioning/         Prometheus + Loki datasources
├── loki/loki.yml                 Log aggregation config
├── k8s/                          Plain Kubernetes manifests
└── helm/prepforge/               Helm chart (backend + worker + migrate hook)
```

## CI/CD (GitHub Actions)
On push/PR to `main`/`master`:
1. **Lint** — `ruff check app tests` (clean; config in `pyproject.toml`).
2. **Test** — `pytest -q` with `ENVIRONMENT=test` (in-memory SQLite; no services needed).
3. **Build & push** — Docker Buildx builds `backend/`, pushes to GHCR as `:latest` and
   `:<sha>` (only on push, with layer caching). Image tag `<sha>` is what CD pins.

## Local / staging — full stack
```bash
cp .env.example .env            # set SECRET_KEY etc.
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d
```
Brings up: **backend** (2 uvicorn workers, runs `alembic upgrade head` on boot),
**worker** (Celery), **postgres** (pgvector), **redis**, **judge0** (code sandbox,
`ALLOW_LOCAL_CODE_EXECUTION=false`), **prometheus** (:9090), **grafana** (:3001),
**loki** (:3100). API at `:8000` (`/docs`, `/metrics`).

## Kubernetes (raw manifests)
```bash
kubectl apply -f infra/k8s/00-namespace.yaml
# Replace ghcr.io/OWNER/REPO and the example Secret values first.
kubectl apply -f infra/k8s/
kubectl -n prepforge rollout status deploy/prepforge-backend
```
Includes: namespace, ConfigMap + Secret (use External Secrets/Vault in real clusters),
Postgres StatefulSet (prefer **managed Postgres** in prod) + Redis, a **migration Job**,
backend + worker Deployments (probes on `/ready` & `/health`, resource requests/limits),
an **HPA** (CPU/memory, 3→20 replicas), and an **NGINX Ingress** with TLS.

## Kubernetes (Helm — recommended)
```bash
helm upgrade --install prepforge infra/helm/prepforge \
  --namespace prepforge --create-namespace \
  --set image.repository=ghcr.io/OWNER/REPO/backend \
  --set image.tag=<git-sha> \
  --set-string secrets.SECRET_KEY=$SECRET_KEY \
  --set-string secrets.DATABASE_URL=$DATABASE_URL \
  --set ingress.host=api.yourdomain.com
```
The chart runs **`alembic upgrade head` as a pre-upgrade hook** (so schema migrates
before the new pods roll), templates the ConfigMap/Secret from `values.yaml`, and gates
the worker, HPA, ingress, and migrations behind flags. Secrets should come from a secret
manager — never commit real values.

## Migration safety
Migrations run as a discrete step (Job / Helm hook), never inside app startup in prod, so
a failed migration blocks the rollout instead of crash-looping pods. Migrations are
additive and reversible (Alembic `downgrade`), and existing functionality is preserved
across releases.

## Production checklist
- [ ] `ENVIRONMENT=production`, strong `SECRET_KEY`, real DB URL via secret manager
- [ ] `ALLOW_LOCAL_CODE_EXECUTION=false` and a reachable `JUDGE0_URL` (sandboxed execution)
- [ ] Managed Postgres (HA + read replica) with `pgvector`; managed Redis
- [ ] TLS at the ingress; restrict `/metrics` to the scrape network
- [ ] Prometheus scraping, Grafana dashboards, Loki logs, Langfuse keys for agent traces
- [ ] HPA tuned; PodDisruptionBudget + multiple replicas for zero-downtime deploys

## Notes / not-yet-done
- The Helm chart was authored to standard syntax but **not** `helm lint`-ed in this
  environment (helm not installed); run `helm lint infra/helm/prepforge` in CI before first use.
- Postgres/Redis are deployed in-cluster for convenience; production should point at
  managed services and drop the StatefulSet/Deployment.
- Celery tasks are scaffolded (ping + a daily-snapshot hook); heavy async jobs plug into
  the existing service layer as they're enabled.
