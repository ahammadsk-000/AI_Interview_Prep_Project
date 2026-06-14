"""Resume / Job / ATS DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.resume.enums import ResumeStatus


class ResumePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime: str
    status: ResumeStatus
    parsed_chars: int = 0
    created_at: datetime

    @classmethod
    def from_orm_resume(cls, r) -> ResumePublic:  # noqa: ANN001
        return cls(
            id=r.id,
            filename=r.filename,
            mime=r.mime,
            status=r.status,
            parsed_chars=len(r.parsed_text or ""),
            created_at=r.created_at,
        )


class JobDescriptionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    raw_text: str = Field(min_length=20, max_length=50_000)


class JobDescriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None = None
    company: str | None = None
    extracted_skills: list[str] = Field(default_factory=list)
    created_at: datetime


class AnalyzeRequest(BaseModel):
    """Analyze a resume, optionally against a saved JD or inline JD text."""

    job_description_id: uuid.UUID | None = None
    jd_text: str | None = Field(default=None, max_length=50_000)


class AtsReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID | None = None
    ats_score: int
    recruiter_score: int
    tech_score: int
    comm_score: int
    readiness: int = 0
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    breakdown: dict = Field(default_factory=dict)
    created_at: datetime

    @classmethod
    def from_orm_report(cls, r) -> AtsReportPublic:  # noqa: ANN001
        readiness = round(
            (r.ats_score + r.recruiter_score + r.tech_score + r.comm_score) / 4
        )
        return cls(
            id=r.id,
            resume_id=r.resume_id,
            job_description_id=r.job_description_id,
            ats_score=r.ats_score,
            recruiter_score=r.recruiter_score,
            tech_score=r.tech_score,
            comm_score=r.comm_score,
            readiness=readiness,
            matched_keywords=r.matched_keywords or [],
            missing_keywords=r.missing_keywords or [],
            suggestions=r.suggestions or [],
            breakdown=r.breakdown or {},
            created_at=r.created_at,
        )


class OptimizeRequest(BaseModel):
    resume_id: uuid.UUID
    job_description_id: uuid.UUID | None = None
    jd_text: str | None = Field(default=None, max_length=50_000)


class OptimizeResponse(BaseModel):
    ats_compatibility: int
    missing_keywords: list[str] = Field(default_factory=list)
    recruiter_insights: list[str] = Field(default_factory=list)
    improved_resume_text: str
    report: AtsReportPublic
