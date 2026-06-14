# PrepForge Frontend

Next.js (App Router) + TypeScript + TailwindCSS + Zustand + React Query web app for the
PrepForge AI Interview Preparation Platform. Dark-mode-first, responsive, Linear/Notion-inspired.

## Quickstart
```bash
cp .env.local.example .env.local      # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                            # http://localhost:3000
```
The dev server proxies `/api/*` to the backend (see `next.config.mjs`), so run the backend
(`uvicorn app.main:app` on :8000) alongside it.

## Scripts
- `npm run dev` — dev server
- `npm run build` / `npm run start` — production build & serve
- `npm run typecheck` — `tsc --noEmit`
- `npm run lint` — ESLint (next/core-web-vitals)

## Structure
```
src/
├── app/
│   ├── layout.tsx · providers.tsx · page.tsx (redirect) · globals.css
│   ├── (auth)/        login · register (+ brand layout)
│   └── (app)/         protected shell (sidebar + topbar + route guard)
│       ├── dashboard · analytics · resume · settings
│       ├── coding · coding/[id] (Monaco editor + run/submit)
│       ├── interview (text + voice modes) · ats · learning · teams
├── components/        ui/* primitives · sidebar · topbar · theme-toggle · voice-recorder · page-header
└── lib/               api (axios + token refresh) · auth-store (zustand) · hooks (react-query) · types · utils
```

## Status — fully wired to the backend
- **Auth** — login/register/refresh/logout
- **Dashboard** — `/analytics/overview` (readiness gauge, stats, dimension breakdown)
- **Analytics** — trend charts (recharts) + interview history
- **Resume** — drag-to-upload (PDF/DOCX/TXT) + parsed list
- **ATS Optimizer** — résumé × job-description analyze + AI résumé rewrite
- **Interview Room** — adaptive Q&A in **text or voice** (MediaRecorder → `/voice/*`)
- **Coding Room** — challenge list → **Monaco editor** with run/submit + DSA evaluation panel
- **Learning Path** — runs the 7-agent career-readiness workflow → readiness, action plan, practice Qs
- **Teams** — create org, manage members, **mentor readiness dashboard**
- **Settings** — profile read/update

Verified: `npm run typecheck`, `npm run lint`, and `npm run build` (15 routes) all pass.
