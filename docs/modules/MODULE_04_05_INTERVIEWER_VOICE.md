# Modules 4 & 5 — AI Interviewer + Voice Interview System

Bounded contexts: **Interview** and **Voice**. Status: **implemented (Phase 3)**.

## Architecture
```
api/v1/endpoints/interview.py   ← REST flow + real-time WebSocket interview room
api/v1/endpoints/voice.py       ← voice session start, audio turn ingest, transcript
services/interview_service.py   ← start · submit_answer (adaptive) · state · end
services/voice_service.py       ← STT → engine → TTS pipeline, transcript/recording persistence
ai/interview_engine.py          ← next-question (LLM + bank fallback) + difficulty adaptation + summary
ai/voice/{base,providers}.py    ← SpeechToText / TextToSpeech ports + stubs (Whisper/ElevenLabs later)
domain/interview/enums.py       ← types, difficulty, statuses, roles
domain/interview/questions.py   ← curated seed question bank (deterministic fallback)
domain/interview/scoring.py     ← answer-signal scorer (drives adaptation)
models/interview.py             ← Interview, InterviewSession, Turn, VoiceSession, Transcript, Recording
repositories/interview.py       ← Interview + Voice repositories
```

**Design choice — deterministic core, LLM augmentation (consistent with Phase 2).**
The engine produces context-aware questions and follow-ups via the `LLMProvider`
port; when no model is reachable (tests/offline) it draws from a curated **question
bank**, never repeating within a session. Difficulty **adapts** to the candidate's
last answer using a deterministic answer-signal score (strong → harder, weak →
easier). Full rubric grading is deferred to Module 8 (Phase 5).

## Interview types & adaptation
`hr · technical · system_design · ml · genai · devops · pm`, each with easy/medium/hard
seed questions. Multi-round ready (`InterviewSession.round`). Personalization hooks via
`Interview.config`.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/interviews/start` | bearer | Begin interview; returns first question |
| POST | `/interviews/sessions/{id}/answer` | bearer (owner) | Submit answer → next question or completion |
| GET | `/interviews/sessions/{id}` | bearer (owner) | Current session state |
| GET | `/interviews/sessions/{id}/turns` | bearer (owner) | Ordered transcript of turns |
| POST | `/interviews/sessions/{id}/end` | bearer (owner) | End early, get summary |
| **WS** | `/interviews/ws/{id}?token=…` | token query | **Real-time interview room** (stream Q → A → Q) |
| POST | `/voice/start` | bearer (owner) | Open a voice session over an interview session |
| POST | `/voice/{id}/turn` | bearer (owner) | Upload audio → STT → engine → TTS (returns transcript + question audio) |
| GET | `/voice/{id}/transcript` | bearer (owner) | Speaker-attributed transcript |

**WebSocket protocol:** server sends `{event: "question", current_question, …}`;
client replies `{answer: "…"}`; repeats until `{event: "summary", done: true}`.

## Voice pipeline (Module 5)
`candidate audio → SpeechToText → InterviewService.submit_answer → next question →
TextToSpeech → recordings + transcripts`. Speaker identification is role-based
(interviewer/candidate). Recordings are stored via the `FileStorage` port for replay.
Real-time **WebRTC** is an edge transport concern; this durable pipeline is the testable
core. STT/TTS sit behind ports — Faster-Whisper/Deepgram and ElevenLabs/Piper drop in
by config without touching call sites.

## Database schema
`interviews`, `interview_sessions`, `turns`, `voice_sessions`, `transcripts`,
`recordings` (migration `0003_interview_voice.py`). See [../DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md).

## Testing
- `tests/test_interview_engine.py` — answer scoring, difficulty adaptation bounds, bank
  fallback never repeats, offline summary.
- `tests/test_interview.py` — start, full flow to completion, reject-after-complete,
  turns/state/ownership (cross-user 404), end; **WebSocket room** (transport-isolated
  with a fake service) + bad-token rejection.
- `tests/test_voice.py` — audio turn transcribe+advance, transcript persistence,
  cross-user 404, full voice session to completion.
- **47 tests total green (~4.8s)**. Migrations 0001→0003 verified to apply in order.

## Security considerations
Per-user ownership on every session/turn/voice resource (others → 404). WebSocket auth
via short-lived access token (`?token=`), decoded without a DB hit; ownership still
enforced in the service. Audio size-capped; stored bytes never logged.

## Scalability considerations
Interview/voice state is durable in Postgres; API stays stateless → horizontal scaling.
STT/TTS and LLM inference are the heavy paths and run behind ports — offloadable to
Celery workers / GPU inference pools independently. WebSocket fan-out scales with a
Redis pub/sub backplane when multi-replica (Phase 10).

## Deployment strategy
No new packages required for the core (stubs are pure-Python). Production wires real
STT/TTS providers (set provider env/creds) and points `LLM_PROVIDER` at Ollama/vLLM;
everything degrades gracefully to the deterministic bank + stub speech if backends are
unavailable.
