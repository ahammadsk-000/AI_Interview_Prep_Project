# Modules 8 & 9 — AI Answer Grading + Behavioral Interview Analyzer

Bounded context: **Evaluation**. Status: **implemented (Phase 5)**.

## Architecture
```
api/v1/endpoints/evaluation.py    ← answer · behavioral · session report · scores
services/evaluation_service.py    ← GradingService (grade answer/behavioral, session report)
ai/grading.py                     ← LLM prose helpers (better/industry answer, recruiter view) + fallbacks
domain/evaluation/rubric.py       ← deterministic 4-dimension rubric scorer
domain/evaluation/star.py         ← STAR-method detector (Situation/Task/Action/Result)
domain/evaluation/grader.py       ← grade_answer + grade_behavioral (deterministic cores)
domain/evaluation/enums.py        ← dimensions, competencies, subject types
models/evaluation.py              ← Score (polymorphic) + FeedbackReport
repositories/evaluation.py        ← Score + FeedbackReport repositories
```

**Design choice — reproducible scores, LLM prose on top.** The numeric grades (rubric
dimensions, STAR coverage, competencies) are deterministic and unit-tested. The LLM
(behind `LLMProvider`) writes the *qualitative* parts — a suggested better answer, an
industry-standard answer, and a recruiter perspective — each with a deterministic
fallback so grading always returns useful output offline.

## Module 8 — AI Answer Grading
Four rubric dimensions (each 0–100): **technical · communication · completeness ·
confidence**, combined into a weighted total and a **score out of 10**. Outputs:
dimension breakdown, rule-based feedback, **suggested better answer**, **industry-standard
answer**.

## Module 9 — Behavioral Interview Analyzer
**STAR detector** flags Situation/Task/Action/Result coverage. Competencies scored:
STAR, communication, **leadership, ownership, teamwork, problem-solving**. Outputs:
behavioral score, competency breakdown, missing STAR components, feedback, and a
**recruiter perspective**.

### Ethics guardrail (Module 10 alignment)
Prompts and scoring judge only the **content and delivery** of an answer — never
protected characteristics — and never make a hiring decision. This is stated in the
recruiter-perspective system prompt.

## Session feedback reports (interview-report generation)
`POST /evaluation/sessions/{id}/grade` pairs each interviewer question with the
candidate's answer, grades every answer, persists per-answer `Score` rows, aggregates
dimension averages into strengths/improvements, and stores a `FeedbackReport`
(PDF export is a later phase via `pdf_key`). This wires Module 8 to the Phase-3
interview engine.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/evaluation/answer` | bearer | Grade a single answer → scores + better/industry answers |
| POST | `/evaluation/behavioral` | bearer | STAR + competency evaluation + recruiter view |
| POST | `/evaluation/sessions/{id}/grade` | bearer (owner) | Grade a whole interview session → feedback report |
| GET | `/evaluation/scores` | bearer | List own scores |
| GET | `/evaluation/scores/{id}` | bearer (owner) | Retrieve one score |

## Database schema
`scores` (polymorphic via `subject_type` + `subject_id`: answer/behavioral/coding/
resume) and `feedback_reports` (overall score, strengths, improvements, detail,
`pdf_key`). Migration `0005_evaluation.py`.

## Testing
- `tests/test_grading.py` — rubric ordering (strong > weak), STAR full-coverage vs
  missing, dimension/feedback shape, behavioral STAR/ownership weighting.
- `tests/test_evaluation_api.py` — answer grading (scores + prose), auth, behavioral
  (STAR result detection + recruiter view), weak < strong, score list/get ownership,
  **session report** (graded answers, per-question, ownership 404, empty-session 422).
- **76 tests total green (~11.6s)**. Migrations 0001→0005 verified to apply in order.

## Security considerations
Per-user ownership on scores and session reports (others → 404). Session grading
ownership flows through the interview service. Answers are size-capped. No protected-
characteristic inference (ethics guardrail above).

## Scalability considerations
Deterministic scoring is cheap and in-process. LLM prose is the heavy path and runs
behind the port — batched/queued via Celery for bulk session grading. `scores`
partitions by user/time at scale and feeds the Phase-7 analytics dashboard directly.

## Deployment strategy
No new packages. Point `LLM_PROVIDER` at Ollama/vLLM for live prose; everything
degrades to deterministic templates if the model is unavailable.
