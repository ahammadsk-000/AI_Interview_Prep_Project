# Module 11 — Multi-Agent Interview System

Bounded context: **Agents**. Status: **implemented (Phase 6)**.

## Architecture
```
api/v1/endpoints/agents.py        ← run workflow, list/get runs, list agents
services/agent_service.py         ← AgentWorkflowService (run + persist + retrieve)
ai/agents/base.py                 ← Agent protocol · AgentContext (blackboard) · WorkflowOrchestrator
ai/agents/agents.py               ← the 7 agents (wrap earlier-phase domain engines)
ai/agents/tracing.py              ← Tracer port + InMemoryTracer (Langfuse later)
domain/agents/enums.py            ← AgentName, RunStatus, StepStatus, role→interview-type map
models/agent.py + migration 0006  ← AgentRun (inputs, output, full step trace, tokens, latency)
repositories/agent.py             ← AgentRun repository
```

## The seven agents
| Agent | Wraps | Output |
|---|---|---|
| **Resume** | Phase-2 analyzer | ATS/recruiter/technical/communication + readiness |
| **ATS** | Phase-2 JD matcher | compatibility %, matched/missing keywords |
| **Interviewer** | Phase-3 question bank | role-mapped interview plan + focus questions |
| **Coding Evaluator** | Phase-4 complexity/quality | static time/space complexity + quality |
| **Behavioral** | Phase-5 grader | STAR + competency scores |
| **Feedback** | synthesis | overall readiness, strengths, improvements |
| **Career Coach** | synthesis + LLM | personalized action plan (focus areas → actions) |

## Orchestration model
A **blackboard + DAG runner**: agents share a mutable `AgentContext` (inputs + accruing
outputs + short-term `memory`). The orchestrator runs them in order, **skips** any whose
inputs are absent, isolates failures (one agent erroring never aborts the run), and
**traces every step** (status, summary, latency, tokens). Feedback and Career-Coach run
last, reading everything upstream produced.

### Why a custom runner (and the LangGraph/CrewAI path)
The runner is framework-free so it is deterministic and unit-testable with the stub LLM
(no graph engine, no network). The `Agent` interface is the seam: **LangGraph** (durable
state, conditional edges, human-in-the-loop, parallel branches) or **CrewAI** (role-based
collaboration) drop in as the production orchestration engine without changing agents or
services. Each agent already isolates a single responsibility and communicates only
through the blackboard — exactly the contract those frameworks expect.

## Agent memory & tracing
- **Short-term** memory: the per-run `AgentContext.memory` scratch (e.g. cached scores
  shared between agents within a run).
- **Long-term** memory: every run persists to `agent_runs` (inputs metadata, full output,
  step trace, tokens, latency, `trace_id`) — queryable per user for trend/recall.
- **Tracing**: the `Tracer` port records each step; `InMemoryTracer` today, **Langfuse**
  in the observability phase behind the same interface.

## API design (`/api/v1`)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/agents` | bearer | List the agents and their roles |
| POST | `/agents/career-readiness` | bearer | Run the workflow over provided inputs |
| GET | `/agents/runs` | bearer | List own runs (with overall readiness) |
| GET | `/agents/runs/{id}` | bearer (owner) | Full run with per-agent trace |

Inputs are all optional; agents run only when their inputs are present (résumé, JD,
behavioral answer, code, target role). At least one input is required.

## Database schema
`agent_runs` — `graph`, `status`, `trace_id`, `inputs` (metadata only, not raw PII),
`output`, `steps` (full trace JSON), `tokens`, `latency_ms`. Migration `0006_agents.py`.

## Testing
- `tests/test_agents.py` — role mapping; full 7-agent run; input-driven skipping;
  feedback aggregation + coach planning.
- `tests/test_agents_api.py` — list agents, full run (7 completed steps + synthesized
  output), partial inputs, empty-input rejection (422), persistence + owner-only access,
  auth.
- **86 tests total green**; migrations 0001→0006 verified to apply in order.

## Security considerations
Per-user ownership on runs (others → 404). Stored `inputs` are **metadata only** (which
signals were provided + target role) — raw résumé/answer/code text is not persisted on
the run. Agent failures are contained and traced, never surfaced as a 500.

## Scalability considerations
Agents are stateless and communicate via the blackboard, so independent branches
parallelize trivially when moved onto LangGraph/CrewAI + Celery workers. Traces stream to
Langfuse; `agent_runs` partitions by user/time. LLM calls (Career-Coach summary) are the
only network hops and sit behind the provider port for batching/queueing.

## Deployment strategy
No new packages for the core runner. Production adds the LangGraph/CrewAI engine and
Langfuse credentials; the workflow degrades to deterministic synthesis when the LLM is
unavailable.
