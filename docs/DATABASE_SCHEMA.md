# Database Schema

PostgreSQL 16 + `pgvector`. UUID primary keys (`uuid_generate_v4`), `created_at`/`updated_at` on every table, soft-delete (`deleted_at`) where audit matters. Naming: `snake_case`, plural tables. FKs `ON DELETE` chosen per aggregate boundary.

## ER Overview (by bounded context)

```
Identity        Resume/Job              Interview/Voice          Coding              Evaluation/Analytics/Learning
────────        ──────────              ───────────────          ──────              ─────────────────────────────
users 1─┐       resumes ───< resume_versions     interviews ──< interview_sessions   coding_challenges ──< coding_submissions
        │       resumes ───< ats_reports         interview_sessions ──< turns        coding_challenges ──< test_cases
roles >─┤       job_descriptions                 voice_sessions ──< transcripts                            │
        │       ats_reports >── job_descriptions voice_sessions ──< recordings                             │
sessions┘                                                                                                   │
subscriptions                                          scores >──────────────────────────────────────────┘
                                                       feedback_reports
                                                       agent_runs
                                                       metric_snapshots
                                                       learning_plans ──< learning_milestones
```

## Tables (Phase 1 = Identity; rest are forward-declared for migrations)

### Identity & Access (Phase 1 — implemented now)

**users**
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| email | citext UNIQUE NOT NULL | login identity |
| hashed_password | text NULL | null for pure-OAuth users |
| full_name | text | |
| avatar_url | text NULL | |
| is_active | bool default true | |
| is_verified | bool default false | email verification |
| target_role | text NULL | e.g. "GenAI Engineer" |
| experience_level | enum(fresher,junior,mid,senior,staff) NULL | |
| created_at / updated_at / deleted_at | timestamptz | |

**roles** — `id`, `name` (enum: ADMIN, MENTOR, RECRUITER, USER), `description`
**user_roles** — m2m `user_id`, `role_id` (PK pair)

**oauth_accounts** — `id`, `user_id` FK, `provider` (google|github), `provider_account_id`, `access_token` (encrypted), unique(`provider`,`provider_account_id`)

**sessions** (refresh tokens) — `id`, `user_id` FK, `refresh_token_hash`, `user_agent`, `ip`, `expires_at`, `revoked_at` NULL

**subscriptions** — `id`, `user_id` FK, `plan` (enum: free, pro, team, enterprise), `status`, `current_period_end`, `seats`

**audit_logs** — `id`, `actor_user_id` NULL, `action`, `resource_type`, `resource_id`, `ip`, `metadata` jsonb, `created_at`

### Resume / Job (Phase 2)
- **resumes** — `id`, `user_id`, `filename`, `storage_key`, `mime`, `parsed_text`, `status`
- **resume_versions** — `id`, `resume_id`, `version`, `content` jsonb, `source` (upload|ai_rewrite)
- **job_descriptions** — `id`, `user_id`, `title`, `company`, `raw_text`, `extracted_skills` jsonb, `embedding` vector
- **ats_reports** — `id`, `resume_id`, `job_description_id` NULL, `ats_score`, `recruiter_score`, `tech_score`, `comm_score`, `missing_keywords` jsonb, `suggestions` jsonb

### Interview / Voice (Phase 3)
- **interviews** — `id`, `user_id`, `type` (hr|technical|system_design|ml|genai|devops|pm), `difficulty`, `status`, `config` jsonb
- **interview_sessions** — `id`, `interview_id`, `round`, `started_at`, `ended_at`, `summary`
- **turns** — `id`, `session_id`, `role` (interviewer|candidate), `content`, `audio_key` NULL, `order_idx`
- **voice_sessions** — `id`, `interview_session_id`, `status`, `provider`
- **transcripts** — `id`, `voice_session_id`, `speaker`, `text`, `ts_start`, `ts_end`
- **recordings** — `id`, `voice_session_id`, `storage_key`, `duration_ms`

### Coding (Phase 4)
- **coding_challenges** — `id`, `slug`, `title`, `difficulty`, `prompt`, `starter_code` jsonb, `tags`, `created_by`
- **test_cases** — `id`, `challenge_id`, `input`, `expected_output`, `is_hidden`, `weight`
- **coding_submissions** — `id`, `user_id`, `challenge_id`, `language`, `source`, `status`, `runtime_ms`, `memory_kb`, `passed`, `total`

### Evaluation / Analytics / Learning (Phase 5–7, 12)
- **scores** — `id`, `subject_type` (answer|coding|behavioral|resume), `subject_id`, `rubric` jsonb, `total`, `breakdown` jsonb
- **feedback_reports** — `id`, `user_id`, `interview_id` NULL, `summary`, `strengths` jsonb, `improvements` jsonb, `pdf_key`
- **agent_runs** — `id`, `user_id`, `graph`, `state` jsonb, `trace_id`, `status`, `tokens`, `latency_ms`
- **metric_snapshots** — `id`, `user_id`, `metric`, `value`, `captured_at` (partition by month)
- **learning_plans** — `id`, `user_id`, `goal`, `roadmap` jsonb, `status`
- **learning_milestones** — `id`, `plan_id`, `title`, `due_at`, `completed_at`

## Indexing & performance
- `users.email` unique btree; `sessions.user_id`, `sessions.refresh_token_hash` btree.
- `turns(session_id, order_idx)`, `coding_submissions(user_id, challenge_id)` composite.
- `embedding` columns: `ivfflat`/`hnsw` (pgvector) for ANN.
- High-volume tables (`turns`, `coding_submissions`, `metric_snapshots`, `audit_logs`) partitioned by month.
- All migrations via Alembic; every schema change is a reviewed, reversible migration.
