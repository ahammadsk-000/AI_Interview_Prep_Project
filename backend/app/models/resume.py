"""Resume / Job / ATS ORM models (Phase 2).

Bounded contexts: Resume and Job. The ``AtsReport`` aggregate links a resume to
an optional job description and stores the computed evaluation. Embedding columns
(pgvector) are deferred to a later phase to keep the schema portable to SQLite
for tests.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, uuid_pk
from app.domain.resume.enums import ResumeSource, ResumeStatus
from app.models.user import JsonType, _enum


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(120), nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ResumeStatus] = mapped_column(
        _enum(ResumeStatus, "resume_status"), default=ResumeStatus.UPLOADED, nullable=False
    )

    versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    reports: Mapped[list[AtsReport]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[dict | None] = mapped_column(JsonType)
    source: Mapped[ResumeSource] = mapped_column(
        _enum(ResumeSource, "resume_source"), default=ResumeSource.UPLOAD, nullable=False
    )

    resume: Mapped[Resume] = relationship(back_populates="versions")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_skills: Mapped[list | None] = mapped_column(JsonType)

    reports: Mapped[list[AtsReport]] = relationship(back_populates="job_description")


class AtsReport(Base):
    __tablename__ = "ats_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("job_descriptions.id", ondelete="SET NULL"), index=True
    )

    ats_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recruiter_score: Mapped[int] = mapped_column(Integer, nullable=False)
    tech_score: Mapped[int] = mapped_column(Integer, nullable=False)
    comm_score: Mapped[int] = mapped_column(Integer, nullable=False)

    matched_keywords: Mapped[list | None] = mapped_column(JsonType)
    missing_keywords: Mapped[list | None] = mapped_column(JsonType)
    suggestions: Mapped[list | None] = mapped_column(JsonType)
    breakdown: Mapped[dict | None] = mapped_column(JsonType)

    resume: Mapped[Resume] = relationship(back_populates="reports")
    job_description: Mapped[JobDescription | None] = relationship(back_populates="reports")
