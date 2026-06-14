"""Coding / DSA DTOs.

Hidden test-case inputs/outputs are never serialized to candidates — only their
pass/fail result is returned.
"""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.coding.enums import ChallengeDifficulty, Language


class TestCaseInput(BaseModel):
    args: list[Any] = Field(default_factory=list)
    expected: Any = None
    is_hidden: bool = False
    weight: int = Field(default=1, ge=1, le=10)


class ChallengeCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=255)
    difficulty: ChallengeDifficulty
    prompt: str = Field(min_length=10, max_length=20_000)
    entrypoint: str = Field(min_length=1, max_length=120)
    starter_code: dict[str, str] | None = None
    tags: list[str] | None = None
    is_public: bool = True
    test_cases: list[TestCaseInput] = Field(min_length=1, max_length=200)


class VisibleTestCase(BaseModel):
    args: list[Any]
    expected: Any


class ChallengeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    difficulty: ChallengeDifficulty
    tags: list[str] = Field(default_factory=list)


class ChallengePublic(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: ChallengeDifficulty
    prompt: str
    entrypoint: str
    starter_code: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    is_public: bool
    visible_test_cases: list[VisibleTestCase] = Field(default_factory=list)
    hidden_test_count: int = 0


class RunRequest(BaseModel):
    language: Language = Language.PYTHON
    source: str = Field(min_length=1, max_length=64_000)


class SubmitRequest(RunRequest):
    pass


class CaseResultPublic(BaseModel):
    index: int
    passed: bool
    is_hidden: bool
    runtime_ms: float | None = None
    error: str | None = None


class SubmissionResultPublic(BaseModel):
    submission_id: uuid.UUID | None = None
    status: str
    passed: int
    total: int
    correctness_score: int
    edge_case_score: int
    code_quality_score: int
    time_complexity: str
    space_complexity: str
    readiness_score: int
    difficulty_rating: str
    runtime_ms: float | None = None
    suggestions: list[str] = Field(default_factory=list)
    complexity_notes: list[str] = Field(default_factory=list)
    cases: list[CaseResultPublic] = Field(default_factory=list)
