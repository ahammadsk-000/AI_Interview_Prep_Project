"""Agent tracing port.

Every agent step is recorded for observability. The default tracer is in-memory
(steps are persisted on the AgentRun). A Langfuse tracer drops in behind the same
Protocol in the observability phase without changing orchestrator code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.domain.agents.enums import StepStatus


@dataclass
class TraceStep:
    agent: str
    status: StepStatus
    summary: str
    latency_ms: float
    tokens: int = 0
    error: str | None = None


@runtime_checkable
class Tracer(Protocol):
    def record(self, step: TraceStep) -> None: ...


@dataclass
class InMemoryTracer:
    trace_id: str
    steps: list[TraceStep] = field(default_factory=list)

    def record(self, step: TraceStep) -> None:
        self.steps.append(step)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens for s in self.steps)

    @property
    def total_latency_ms(self) -> float:
        return round(sum(s.latency_ms for s in self.steps), 2)


def flush_to_langfuse(trace_id: str, graph: str, steps: list[TraceStep]) -> None:
    """Forward a completed agent trace to Langfuse (lazy import, no-op if unset).

    Wires the Phase-6 tracer to the production LLM-observability backend without
    coupling the orchestrator to any vendor.
    """
    from app.core.config import settings

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return
    try:  # pragma: no cover - exercised only when Langfuse is configured + installed
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        trace = client.trace(id=trace_id, name=graph)
        for s in steps:
            trace.span(name=s.agent, metadata={"status": s.status.value, "summary": s.summary},
                       start_time=None)
        client.flush()
    except Exception:  # pragma: no cover - never let tracing break a run
        pass
