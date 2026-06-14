# Deploy PrepForge for free (Vercel + Render + Neon)

This puts the app online for **$0** with **automatic deploys on every `git push`**:

| Part | Host | Free tier |
|---|---|---|
| Frontend (Next.js) | **Vercel** | Hobby (free) |
| Backend (FastAPI) | **Render** | Free Web Service |
| Database (Postgres) | **Neon** | Free serverless Postgres |
| AI (optional) | **Groq** | Free OpenAI-compatible API |

You only do these steps **once**. After that, pushing to GitHub `main` redeploys both the
frontend and backend automatically.

> The repo already contains `render.yaml` (backend blueprint) and a Next.js frontend that
> Vercel auto-detects. You just connect the accounts.

---

## Step 1 — Database: Neon (free Postgres)

1. Go to **https://neon.tech** → sign up (use *Continue with GitHub*).
2. Create a project (any name, e.g. `prepforge`). A database is created automatically.
3. On the project dashboard, copy the **connection string**. It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
   ```
4. **Convert it for this app** (two edits):
   - change `postgresql://` → `postgresql+asyncpg://`
   - change `?sslmode=require` → `?ssl=require`
   
   Final value to use as `DATABASE_URL`:
   ```
   postgresql+asyncpg://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/neondb?ssl=require
   ```
   Keep this handy for Step 2.

---

## Step 2 — Backend: Render (FastAPI)

1. Go to **https://render.com** → sign up with GitHub.
2. **New → Blueprint** → select your repo `ahammadsk-000/AI_Interview_Prep_Project`.
   Render reads `render.yaml` and proposes a service called **prepforge-backend**.
3. When prompted for the environment variables marked "set manually", enter:
   - `DATABASE_URL` = the Neon string from Step 1 (the `postgresql+asyncpg://…?ssl=require` form)
   - `BACKEND_CORS_ORIGINS` = `["https://localhost"]` for now (you'll update it in Step 4)
4. Click **Apply / Create**. Render builds and starts the backend; the first build takes a
   few minutes. When it's live you'll get a URL like:
   ```
   https://prepforge-backend.onrender.com
   ```
5. Verify it: open `https://prepforge-backend.onrender.com/health` → `{"status":"ok"}`, and
   `…/docs` for the API. (On the free plan the service sleeps after ~15 min idle, so the
   first request after a nap takes ~30–60s — normal.)

---

## Step 3 — Frontend: Vercel (Next.js)

1. Go to **https://vercel.com** → sign up with GitHub → **Add New → Project** → import the repo.
2. In the import screen set:
   - **Root Directory** = `frontend`   ← important (the Next.js app lives there)
   - Framework Preset = **Next.js** (auto-detected)
3. Add an **Environment Variable**:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://prepforge-backend.onrender.com` (your Render URL)
4. Click **Deploy**. You'll get a URL like `https://ai-interview-prep-project.vercel.app`.

The frontend proxies `/api/*` to your backend automatically (via `next.config.mjs`), so the
browser stays same-origin.

---

## Step 4 — Connect them (CORS)

1. Back in **Render → prepforge-backend → Environment**, set:
   - `BACKEND_CORS_ORIGINS` = `["https://<your-app>.vercel.app"]` (your real Vercel URL)
2. Save — Render redeploys. Done: open your Vercel URL, register, and use the app.

---

## Step 5 (optional) — Free real AI with Groq

Without this, AI text uses built-in deterministic fallbacks (the app fully works). To get
dynamic LLM answers/questions for free:

1. Get a free API key at **https://console.groq.com** (Continue with GitHub).
2. In **Render → Environment** set:
   - `LLM_PROVIDER` = `openai_compatible`
   - `OPENAI_API_KEY` = your Groq key
   - (`OPENAI_BASE_URL` and `LLM_MODEL` are already set by the blueprint.)
3. Save → redeploy.

---

## Automatic deploys (already on)

- **Render**: `autoDeploy: true` in `render.yaml` → every push to `main` rebuilds the backend
  and runs DB migrations on startup.
- **Vercel**: auto-deploys every push to `main` by default; pull requests get preview URLs.

So your normal workflow is just:
```bash
git add -A && git commit -m "my change" && git push
```
…and both live sites update on their own.

---

## Notes & gotchas

- **Coding Room execution stays disabled in production** (`ALLOW_LOCAL_CODE_EXECUTION=false`)
  because running untrusted user code on a shared host is unsafe. Everything else (interviews,
  résumé/ATS, grading, analytics, learning, teams) works fully. To enable code execution
  later, run/point to a **Judge0** instance and set `JUDGE0_URL`.
- **Database migrations** run automatically on backend startup (`alembic upgrade head`), and
  starter coding challenges + roles are seeded on first boot.
- **No Redis** is used on the free tier (`RATE_LIMIT_ENABLED=false`, `CACHE_ENABLED=false`).
  To add it later, create a free **Upstash** Redis and set `REDIS_URL` + flip those flags.
- **Custom domain**: both Vercel and Render let you attach a custom domain for free (you pay
  only for the domain name itself).
