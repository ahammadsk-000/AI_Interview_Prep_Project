# Modules 6 & 7 — Coding Interview Platform + DSA Evaluation Engine

Bounded context: **Coding**. Status: **implemented (Phase 4)**.

## Architecture
```
api/v1/endpoints/coding.py        ← challenges (author/list/get), run, submit, get submission
services/coding_service.py        ← ChallengeService · SubmissionService (run/submit)
ai/execution/base.py              ← ExecutionEngine port + request/result dataclasses
ai/execution/local_python.py      ← real Python runner (DEV/TEST ONLY — explicit safety boundary)
ai/execution/judge0.py            ← Judge0 sandbox adapter (production) — scaffold
ai/execution/factory.py           ← engine selection (Judge0 if configured, else local)
domain/coding/complexity.py       ← AST/regex time & space complexity estimation
domain/coding/quality.py          ← static code-quality scoring
domain/coding/evaluator.py        ← combines execution + analysis → CodingEvaluation
models/coding.py                  ← CodingChallenge, TestCase, CodingSubmission
repositories/coding.py            ← Challenge + Submission repositories
```

**Design choice — pluggable execution, deterministic evaluation.** Code runs behind
the `ExecutionEngine` port. Production uses **Judge0/Docker** isolation; dev/tests use
a local Python runner. The DSA evaluation (correctness + complexity + quality) is
deterministic and runs on top of whatever the engine returns.

### ⚠️ Code-execution safety boundary
Running untrusted code is the platform's highest-risk surface. The local runner
(`local_python.py`) executes submissions in a child process with a wall-clock timeout
but is **not** a security sandbox (no fs/network/syscall isolation). It is gated by
`ALLOW_LOCAL_CODE_EXECUTION` and the factory never prefers it when `JUDGE0_URL` is set.
**Production must run on Judge0 / gVisor / Firecracker.** This is called out loudly in
code so it can't be enabled by accident.

## Languages
Python (executes locally today) · Java · JavaScript · Go · C++ · C# (via Judge0 in
production; the local engine returns `unsupported` for non-Python so grading never
silently lies). Monaco editor integration is frontend (later phase); `starter_code`
per language is stored on the challenge.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/coding/challenges` | bearer + `MENTOR`/`ADMIN` | Author a challenge (visible + hidden cases) |
| GET | `/coding/challenges` | bearer | List visible challenges |
| GET | `/coding/challenges/{id}` | bearer | Challenge prompt + **visible** cases (hidden never leaked) |
| POST | `/coding/challenges/{id}/run` | bearer | Quick run vs visible cases (no persistence) |
| POST | `/coding/challenges/{id}/submit` | bearer | Full run (incl. hidden) → evaluation, persisted |
| GET | `/coding/submissions/{id}` | bearer (owner) | Retrieve a past submission's evaluation |

## DSA Evaluation outputs (Module 7)
Per submission: correctness score, **edge-case score** (hidden-case pass rate),
code-quality score, **time & space complexity** estimates, **interview-readiness
score**, difficulty rating, and concrete improvement suggestions. Complexity is an
explicit *estimate* (AST loop-nesting/recursion/sort detection for Python; regex
heuristics otherwise) — labelled as such, not a proof.

## Database schema
`coding_challenges`, `test_cases` (visible/hidden + weight), `coding_submissions`
(status, passed/total, runtime, evaluation JSON). Migration `0004_coding.py`. Expected
outputs are JSON-wrapped (`{"value": …}`) so any value type round-trips.

## Testing
- `tests/test_complexity.py` — complexity estimation (constant/linear/nested/sort/
  exponential), quality penalties, evaluator combination.
- `tests/test_coding.py` — **executes real Python** end-to-end: create (hides hidden
  cases), RBAC (regular user 403), run vs submit, correct/wrong/syntax-error/unsupported
  outcomes, hidden-case non-leakage, owner-only submission retrieval.
- **63 tests total green (~6.8s)**. Migrations 0001→0004 verified to apply in order.

## Security considerations
RBAC on authoring (`MENTOR`/`ADMIN`); ownership on submissions (others → 404). Hidden
test cases, their inputs/outputs, and even hidden-case timing/errors are never returned
to candidates. Submission source size-capped (`MAX_SOURCE_BYTES`). Execution gated and
sandbox-first; timeouts prevent infinite loops from hanging workers.

## Scalability considerations
Execution is the heavy, isolated path — it runs on a dedicated, autoscaled node pool
via Judge0 (or Celery-dispatched sandboxes), decoupled from the API. Static evaluation
is cheap and in-process. Challenges/test cases are cacheable; submissions partition by
user/time at scale.

## Deployment strategy
Set `JUDGE0_URL`/`JUDGE0_KEY` and `ALLOW_LOCAL_CODE_EXECUTION=false` in production. No
extra Python packages for the core (AST/regex only). The Judge0 service ships as its own
deployment in the Phase-9 manifests.
