"""Evaluation DTOs (answer grading, behavioral, session feedback report)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.evaluation.enums import SubjectType


class GradeAnswerRequest(BaseModel):
    question: str | None = Field(default=None, max_length=4_000)
    answer: str = Field(min_length=1, max_length=20_000)
    subject_id: uuid.UUID | None = None  # e.g. an interview turn id


class AnswerGradePublic(BaseModel):
    score_id: uuid.UUID | None = None
    total: int
    score_out_of_10: float
    dimensions: dict[str, int]
    feedback: list[str] = Field(default_factory=list)
    suggested_better_answer: str
    industry_standard_answer: str


class BehavioralRequest(BaseModel):
    question: str | None = Field(default=None, max_length=4_000)
    answer: str = Field(min_length=1, max_length=20_000)
    subject_id: uuid.UUID | None = None


class BehavioralGradePublic(BaseModel):
    score_id: uuid.UUID | None = None
    behavioral_score: int
    competencies: dict[str, int]
    star_components: dict[str, bool]
    missing_star: list[str] = Field(default_factory=list)
    feedback: list[str] = Field(default_factory=list)
    recruiter_perspective: str


class ScorePublic(BaseModel):
    id: uuid.UUID
    subject_type: SubjectType
    subject_id: uuid.UUID | None = None
    question: str | None = None
    total: int
    breakdown: dict = Field(default_factory=dict)
    created_at: datetime


class SessionReportPublic(BaseModel):
    report_id: uuid.UUID
    interview_session_id: uuid.UUID
    overall_score: int
    graded_answers: int
    summary: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    per_question: list[dict] = Field(default_factory=list)
