"""Agent base + orchestrator (a deterministic blackboard DAG runner).

Agents share a mutable ``AgentContext`` (the blackboard): each reads the inputs/
prior outputs it needs and writes its own outputs back. The orchestrator runs them
in order, skipping any whose inputs are absent, and traces every step.

This is intentionally framework-free so it is fast and unit-testable. LangGraph /
CrewAI can replace the runner behind the same ``Agent`` interface for production
(durable state, human-in-the-loop, parallel branches) — see the module doc.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.ai.agents.tracing import InMemoryTracer, TraceStep
from app.ai.llm.base import LLMProvider
from app.domain.agents.enums import AgentName, StepStatus


@dataclass
class AgentContext:
    """Shared blackboard for one workflow run."""

    inputs: dict[str, Any]
    llm: LLMProvider
    outputs: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)  # short-term scratch within a run

    def has(self, *keys: str) -> bool:
        return all(self.inputs.get(k) not in (None, "", []) for k in keys)


@dataclass
class AgentResult:
    key: str
    value: Any
    summary: str
    tokens: int = 0


@runtime_checkable
class Agent(Protocol):
    name: AgentName

    def applies(self, ctx: AgentContext) -> bool: ...
    async def run(self, ctx: AgentContext) -> AgentResult: ...


class WorkflowOrchestrator:
    def __init__(self, agents: list[Agent], *, name: str) -> None:
        self._agents = agents
        self.name = name

    async def run(self, ctx: AgentContext, tracer: InMemoryTracer) -> dict[str, Any]:
        for agent in self._agents:
            if not agent.applies(ctx):
                tracer.record(TraceStep(
                    agent=agent.name.value, status=StepStatus.SKIPPED,
                    summary="Skipped — required inputs not provided.", latency_ms=0.0,
                ))
                continue
            t0 = time.perf_counter()
            try:
                result = await agent.run(ctx)
                ctx.outputs[result.key] = result.value
                tracer.record(TraceStep(
                    agent=agent.name.value, status=StepStatus.COMPLETED,
                    summary=result.summary,
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                    tokens=result.tokens,
                ))
            except Exception as exc:  # one agent failing must not abort the workflow
                tracer.record(TraceStep(
                    agent=agent.name.value, status=StepStatus.ERROR,
                    summary="Agent raised an exception.",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                    error=f"{type(exc).__name__}: {exc}",
                ))
        return ctx.outputs
