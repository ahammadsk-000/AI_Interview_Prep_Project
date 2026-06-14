"""Multi-agent workflow use-cases.

Runs the career-readiness orchestration over the seven agents, persists the run +
full trace (agent memory + observability), and exposes retrieval. Inputs are stored
as lightweight metadata (which signals were provided) rather than raw PII text.
"""
from __future__ import annotations

import uuid

from app.ai.agents.agents import career_readiness_agents
from app.ai.agents.base import AgentContext, WorkflowOrchestrator
from app.ai.agents.tracing import InMemoryTracer, flush_to_langfuse
from app.ai.llm.base import LLMProvider
from app.core import metrics
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.agents.enums import AgentName, RunStatus, StepStatus
from app.models.agent import AgentRun
from app.repositories.agent import AgentRunRepository
from app.schemas.agent import AgentDescriptor, CareerReadinessRequest

GRAPH_NAME = "career_readiness"

AGENT_ROLES = {
    AgentName.RESUME: "Analyzes the résumé for ATS, recruiter, technical and communication signals.",
    AgentName.ATS: "Matches the résumé against a job description and finds keyword gaps.",
    AgentName.INTERVIEWER: "Builds a role-specific interview plan with focus questions.",
    AgentName.CODING_EVALUATOR: "Statically reviews code for complexity and quality.",
    AgentName.BEHAVIORAL: "Evaluates a behavioral answer (STAR + competencies).",
    AgentName.FEEDBACK: "Synthesizes all signals into an overall readiness verdict.",
    AgentName.CAREER_COACH: "Turns weaknesses into a personalized action plan.",
}


class AgentWorkflowService:
    def __init__(self, runs: AgentRunRepository, llm: LLMProvider) -> None:
        self._runs = runs
        self._llm = llm

    @staticmethod
    def list_agents() -> list[AgentDescriptor]:
        return [AgentDescriptor(name=n.value, role=r) for n, r in AGENT_ROLES.items()]

    async def run_career_readiness(
        self, user_id: uuid.UUID, req: CareerReadinessRequest
    ) -> AgentRun:
        inputs = {
            "target_role": req.target_role,
            "resume_text": req.resume_text,
            "jd_text": req.jd_text,
            "behavioral_answer": req.behavioral_answer,
            "code": req.code,
            "language": req.language.value,
        }
        if not any(inputs[k] for k in
                   ("resume_text", "jd_text", "behavioral_answer", "code", "target_role")):
            raise ValidationError("Provide at least one input for the workflow to act on.")

        ctx = AgentContext(inputs=inputs, llm=self._llm)
        tracer = InMemoryTracer(trace_id=uuid.uuid4().hex)
        orchestrator = WorkflowOrchestrator(career_readiness_agents(), name=GRAPH_NAME)

        outputs = await orchestrator.run(ctx, tracer)
        completed = any(s.status == StepStatus.COMPLETED for s in tracer.steps)
        run_status = RunStatus.COMPLETED if completed else RunStatus.FAILED

        # Observability: count the run and forward the trace to Langfuse if configured.
        metrics.agent_runs_total.inc(graph=GRAPH_NAME, status=run_status.value)
        flush_to_langfuse(tracer.trace_id, GRAPH_NAME, tracer.steps)

        run = AgentRun(
            user_id=user_id, graph=GRAPH_NAME,
            status=run_status,
            trace_id=tracer.trace_id,
            inputs={
                "target_role": req.target_role,
                "provided": [k for k in ("resume_text", "jd_text", "behavioral_answer", "code")
                             if inputs[k]],
            },
            output=outputs,
            steps=[
                {
                    "agent": s.agent, "status": s.status.value, "summary": s.summary,
                    "latency_ms": s.latency_ms, "tokens": s.tokens, "error": s.error,
                }
                for s in tracer.steps
            ],
            tokens=tracer.total_tokens,
            latency_ms=tracer.total_latency_ms,
        )
        return await self._runs.add(run)

    async def get_owned_run(self, run_id: uuid.UUID, user_id: uuid.UUID) -> AgentRun:
        run = await self._runs.get(run_id)
        if run is None or run.user_id != user_id:
            raise NotFoundError("Agent run not found.")
        return run

    async def list_runs(self, user_id: uuid.UUID, **kw):
        return await self._runs.list_for_user(user_id, **kw)
