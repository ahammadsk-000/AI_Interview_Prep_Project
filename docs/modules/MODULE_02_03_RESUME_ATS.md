# Modules 2 & 3 — Resume Analyzer + ATS Optimization Engine

Bounded contexts: **Resume** and **Job**. Status: **implemented (Phase 2)**.

## Architecture
```
api/v1/endpoints/resume.py            ← transport (upload, list, analyze, JD, optimize)
services/resume_service.py            ← ResumeService · JobService · AtsService (use-cases)
services/parsing/document_parser.py   ← PDF/DOCX/TXT extraction + secure-upload validation
services/storage.py                   ← FileStorage port + LocalFileStorage (S3/MinIO later)
domain/resume/analyzer.py             ← deterministic 0–100 scoring engine (no LLM)
domain/resume/skills.py               ← curated skills taxonomy + extraction
domain/resume/enums.py                ← ResumeStatus, sections, file types
ai/llm/{base,providers}.py            ← LLMProvider port: Ollama · OpenAI-compat/vLLM · Stub
repositories/resume.py                ← Resume / JobDescription / AtsReport repos (+ version control)
models/resume.py                      ← Resume, ResumeVersion, JobDescription, AtsReport
```

**Design choice — deterministic core, LLM augmentation.** Scoring is rule-based and
reproducible (testable, no model weights, no network). The LLM only adds prose
rewrites/suggestions *on top of* the numeric report, behind the `LLMProvider` port.
In tests and offline, a `StubProvider` + deterministic rewrite keep everything working.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/resumes` | bearer | Upload résumé (multipart) → parse + store |
| GET | `/resumes` | bearer | List own résumés (paginated) |
| GET | `/resumes/{id}` | bearer (owner) | Fetch one résumé |
| POST | `/resumes/{id}/analyze` | bearer (owner) | ATS report (optional JD by id or inline text) |
| POST | `/job-descriptions` | bearer | Create JD, auto-extract skills |
| POST | `/ats/optimize` | bearer (owner) | ATS %, missing keywords, rewritten résumé, recruiter insights |

**Outputs** (Module 2 & 3 requirements): ATS score, recruiter score, technical-skill
score, communication score, readiness, matched/missing keywords, improvement
suggestions, ATS compatibility %, improved résumé version, recruiter insights.

## Scoring model (0–100, explainable)
- **ats_score** = sections (0.35) + contact completeness (0.20) + keyword match (0.35) + bullets (0.10)
- **recruiter_score** = sections + quantified achievements + action verbs + bullets + length
- **tech_score** = JD coverage (or skill volume) + category diversity
- **comm_score** = quantification + action verbs + bullets + length
- Every component + raw signals returned in `breakdown` for transparency.

## Database schema
Tables `resumes`, `resume_versions`, `job_descriptions`, `ats_reports` (migration
`0002_resume_ats.py`). JSON columns use generic `JSON` (JSONB on Postgres). Résumé
**version control** via `resume_versions` (each AI rewrite is a new version). Full
columns in [../DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md).

## Testing
- `tests/test_analyzer.py` — unit tests: skill extraction (word-boundary correctness),
  strong vs weak résumé scoring, JD gap detection, score bounds.
- `tests/test_resume.py` — API: TXT & DOCX upload + parse, unsupported/fake-PDF
  rejection, auth + cross-user ownership (404), analyze with/without JD, saved-JD
  flow, JD skill extraction, optimize. In-memory SQLite + temp storage + Stub LLM.
- **32 tests total green (~2.4s)**.

## Security considerations
- **Secure upload**: extension allow-list, size cap (`MAX_UPLOAD_BYTES`), magic-byte
  sniffing (PDF `%PDF-`, DOCX zip `PK`), filename sanitization (path-traversal safe),
  empty-file rejection. Ownership enforced in services (other users → 404, no leak).
- Storage keys namespaced per user; OAuth/file bytes never logged.

## Scalability considerations
- Parsing/scoring is CPU-bound and fast; heavy or batch parsing + embedding indexing
  moves to **Celery workers** (already provisioned). Storage port swaps to S3/MinIO
  for horizontal scale. JD/résumé **pgvector embeddings** (SentenceTransformers) are a
  planned augmentation for fuzzy semantic matching — schema/port ready, not yet wired.

## Deployment strategy
No new infra: ships with the existing backend image. Adds `pypdf` + `python-docx`
deps. Set `STORAGE_DIR` (or S3 creds in a later phase) and `LLM_PROVIDER`/`OLLAMA_BASE_URL`
for live rewrites; everything degrades gracefully to deterministic output if the LLM
is unreachable.
