# Module 1 — Authentication & User Management

Bounded context: **Identity & Access**. Status: **implemented (Phase 1)**.

## Architecture
Clean layering inside the modular monolith:
```
api/v1/endpoints/auth.py , users.py        ← transport (FastAPI)
api/v1/deps.py                             ← auth + RBAC dependencies
services/auth_service.py                   ← use-cases (register/login/refresh/logout)
repositories/user.py , session.py          ← data access (ports + SQLAlchemy)
domain/identity/enums.py                   ← framework-free domain values
models/user.py                             ← ORM (User, Role, Session, OAuthAccount, Subscription, AuditLog)
core/security.py                           ← Argon2id + JWT primitives
```

## Folder structure
See [../ARCHITECTURE.md](../ARCHITECTURE.md#3-backend-architecture-layered). Files above are the Module-1 slice.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | public | Create account, issue token pair |
| POST | `/auth/login` | public | Authenticate, issue token pair |
| POST | `/auth/refresh` | public (refresh token) | Rotate refresh → new pair |
| POST | `/auth/logout` | public (refresh token) | Revoke refresh session |
| GET | `/users/me` | bearer | Current profile |
| PATCH | `/users/me` | bearer | Update profile |
| GET | `/users` | bearer + `ADMIN` | Paginated user directory |
| GET | `/health`, `/ready` | public | Liveness / readiness |

OpenAPI served at `/docs` and `/api/v1/openapi.json`.

## Database schema
Tables: `users`, `roles`, `user_roles`, `oauth_accounts`, `sessions`, `subscriptions`, `audit_logs`. Full columns in [../DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md#identity--access-phase-1--implemented-now). Migration: `alembic/versions/0001_initial_identity.py`.

## Testing
`tests/test_auth.py` covers register (+ duplicate/weak-password), login (success/wrong/unknown), `/me` (auth required + token), profile update, refresh rotation + reuse rejection, logout revocation, RBAC denial, health. Runs on in-memory async SQLite — no external services needed. `pytest -q`.

## Security considerations
- **Argon2id** password hashing; refresh tokens stored **hashed** (SHA-256), never raw.
- **JWT**: short-lived access (15 min) + rotating refresh (14 d); `type` claim checked; rotation revokes the presented token, reuse is rejected (replay detection).
- **RBAC** via `require_roles(...)` dependency; roles embedded in access token + re-checked against DB.
- Timing-equalized auth failures; rate limiting; security headers; CORS allow-list.
- OAuth tokens column reserved for encryption-at-rest in production.

## Scalability considerations
Stateless API (JWT) → horizontal replicas. Session/revocation state in Postgres (movable to Redis denylist for very high throughput). `sessions` table indexed on `user_id` and `refresh_token_hash`; partition by month if volume warrants.

## Deployment strategy
`docker compose up` (Postgres+Redis+backend, runs `alembic upgrade head` on boot). Production: container image → Kubernetes Deployment + HPA, managed Postgres/Redis, secrets via External Secrets/Vault (Phase 9).

## OAuth (Google/GitHub) — scaffolded
`OAuthAccount` model, `OAuthProvider` enum, and config keys are in place. Authorization-code flow endpoints land alongside the email-verification flow in a Phase-1.x follow-up; the data model already supports linking provider identities to a `User`.
