"""Multi-agent ORM model (Phase 6): AgentRun.

One row per workflow execution, capturing inputs, the synthesized output, the full
per-agent trace, and aggregate cost/latency for observability and agent memory.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, uuid_pk
from app.domain.agents.enums import RunStatus
from app.models.user import JsonType, _enum


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    graph: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        _enum(RunStatus, "agent_run_status"), default=RunStatus.RUNNING, nullable=False
    )
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    inputs: Mapped[dict | None] = mapped_column(JsonType)
    output: Mapped[dict | None] = mapped_column(JsonType)
    steps: Mapped[list | None] = mapped_column(JsonType)
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
