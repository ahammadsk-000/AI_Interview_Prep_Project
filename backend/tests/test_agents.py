"""Unit tests for the agent orchestrator and agents (no DB, Stub LLM)."""
from __future__ import annotations

import pytest

from app.ai.agents.agents import career_readiness_agents
from app.ai.agents.base import AgentContext, WorkflowOrchestrator
from app.ai.agents.tracing import InMemoryTracer
from app.ai.llm.providers import StubProvider
from app.domain.agents.enums import AgentName, StepStatus, role_to_interview_type
from app.domain.interview.enums import InterviewType

RESUME = (
    "Senior ML Engineer. Experience: led a RAG platform with Python, FastAPI, pgvector, "
    "reducing latency 40%. Skills: PyTorch, Docker, Kubernetes. Education: B.Tech."
)
JD = "We need Python, Kubernetes, Terraform and Go for this ML platform role."
BEHAVIORAL = (
    "The situation was a failing service. My task was reliability. I led the fix: first I "
    "analyzed the root cause, then implemented caching. As a result errors dropped 60%."
)
CODE = "def add(a, b):\n    return a + b\n"


def _ctx(**inputs):
    base = {"target_role": None, "resume_text": None, "jd_text": None,
            "behavioral_answer": None, "code": None, "language": "python"}
    base.update(inputs)
    return AgentContext(inputs=base, llm=StubProvider())


def test_role_mapping():
    assert role_to_interview_type("GenAI Engineer") == InterviewType.GENAI
    assert role_to_interview_type("DevOps/SRE") == InterviewType.DEVOPS
    assert role_to_interview_type("Product Manager") == InterviewType.PM
    assert role_to_interview_type(None) == InterviewType.TECHNICAL


@pytest.mark.asyncio
async def test_orchestrator_runs_all_applicable_agents():
    ctx = _ctx(target_role="GenAI Engineer", resume_text=RESUME, jd_text=JD,
               behavioral_answer=BEHAVIORAL, code=CODE)
    tracer = InMemoryTracer(trace_id="t1")
    orch = WorkflowOrchestrator(career_readiness_agents(), name="career_readiness")
    outputs = await orch.run(ctx, tracer)

    # All seven agents have inputs → all complete.
    completed = [s for s in tracer.steps if s.status == StepStatus.COMPLETED]
    assert len(completed) == 7
    assert {"resume", "ats", "interview_plan", "coding", "behavioral",
            "feedback", "career_plan"} <= set(outputs)
    assert 0 <= outputs["feedback"]["overall_readiness"] <= 100


@pytest.mark.asyncio
async def test_agents_skip_when_inputs_missing():
    ctx = _ctx(behavioral_answer=BEHAVIORAL)  # only behavioral provided
    tracer = InMemoryTracer(trace_id="t2")
    orch = WorkflowOrchestrator(career_readiness_agents(), name="career_readiness")
    outputs = await orch.run(ctx, tracer)

    statuses = {s.agent: s.status for s in tracer.steps}
    assert statuses[AgentName.RESUME.value] == StepStatus.SKIPPED
    assert statuses[AgentName.ATS.value] == StepStatus.SKIPPED
    assert statuses[AgentName.BEHAVIORAL.value] == StepStatus.COMPLETED
    # Feedback still runs because behavioral produced output.
    assert statuses[AgentName.FEEDBACK.value] == StepStatus.COMPLETED
    assert "behavioral" in outputs and "feedback" in outputs


@pytest.mark.asyncio
async def test_feedback_aggregates_signals_and_coach_plans():
    ctx = _ctx(target_role="ML Engineer", resume_text=RESUME, code=CODE)
    tracer = InMemoryTracer(trace_id="t3")
    orch = WorkflowOrchestrator(career_readiness_agents(), name="career_readiness")
    outputs = await orch.run(ctx, tracer)

    assert "feedback" in outputs
    assert "career_plan" in outputs
    assert outputs["career_plan"]["focus_areas"]
    assert outputs["interview_plan"]["interview_type"] == "ml"
