"""Multi-agent workflow DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.coding.enums import Language


class CareerReadinessRequest(BaseModel):
    """All fields optional — agents run only when their inputs are present."""

    target_role: str | None = Field(default=None, max_length=160)
    resume_text: str | None = Field(default=None, max_length=50_000)
    jd_text: str | None = Field(default=None, max_length=50_000)
    behavioral_answer: str | None = Field(default=None, max_length=20_000)
    code: str | None = Field(default=None, max_length=64_000)
    language: Language = Language.PYTHON


class AgentStepPublic(BaseModel):
    agent: str
    status: str
    summary: str
    latency_ms: float
    tokens: int = 0
    error: str | None = None


class AgentRunPublic(BaseModel):
    id: uuid.UUID
    graph: str
    status: str
    trace_id: str
    output: dict = Field(default_factory=dict)
    steps: list[AgentStepPublic] = Field(default_factory=list)
    tokens: int = 0
    latency_ms: float | None = None
    created_at: datetime


class AgentRunSummary(BaseModel):
    id: uuid.UUID
    graph: str
    status: str
    overall_readiness: int | None = None
    tokens: int = 0
    created_at: datetime


class AgentDescriptor(BaseModel):
    name: str
    role: str
