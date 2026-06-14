"""Evaluation ORM models (Phase 5): Score + FeedbackReport.

``Score`` is a generic, polymorphic grading record (answer / behavioral / coding /
resume) keyed by ``subject_type`` + optional ``subject_id``. ``FeedbackReport``
aggregates a session's grades into a shareable report (PDF export later).
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, uuid_pk
from app.domain.evaluation.enums import SubjectType
from app.models.user import JsonType, _enum


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_type: Mapped[SubjectType] = mapped_column(_enum(SubjectType, "score_subject_type"))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    question: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    breakdown: Mapped[dict | None] = mapped_column(JsonType)
    feedback: Mapped[dict | None] = mapped_column(JsonType)


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interview_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list | None] = mapped_column(JsonType)
    improvements: Mapped[list | None] = mapped_column(JsonType)
    detail: Mapped[dict | None] = mapped_column(JsonType)
    pdf_key: Mapped[str | None] = mapped_column(String(512))
