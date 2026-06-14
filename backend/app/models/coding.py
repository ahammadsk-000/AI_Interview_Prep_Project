"""Coding / DSA ORM models (Phase 4).

Bounded context: Coding. A ``CodingChallenge`` owns ``TestCase`` rows (visible +
hidden); a ``CodingSubmission`` records a run and its DSA evaluation.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, uuid_pk
from app.domain.coding.enums import ChallengeDifficulty, Language, SubmissionStatus
from app.models.user import JsonType, _enum


class CodingChallenge(Base):
    __tablename__ = "coding_challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[ChallengeDifficulty] = mapped_column(
        _enum(ChallengeDifficulty, "challenge_difficulty"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    entrypoint: Mapped[str] = mapped_column(String(120), nullable=False)
    starter_code: Mapped[dict | None] = mapped_column(JsonType)  # {language: code}
    tags: Mapped[list | None] = mapped_column(JsonType)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )
    submissions: Mapped[list[CodingSubmission]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = uuid_pk()
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("coding_challenges.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    args: Mapped[list | None] = mapped_column(JsonType)       # positional args (JSON)
    expected_output: Mapped[dict | None] = mapped_column(JsonType)  # JSON-wrapped value
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    challenge: Mapped[CodingChallenge] = relationship(back_populates="test_cases")


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("coding_challenges.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    language: Mapped[Language] = mapped_column(_enum(Language, "submission_language"))
    source: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        _enum(SubmissionStatus, "submission_status"),
        default=SubmissionStatus.PENDING, nullable=False,
    )
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runtime_ms: Mapped[float | None] = mapped_column(Float)
    memory_kb: Mapped[int | None] = mapped_column(Integer)
    evaluation: Mapped[dict | None] = mapped_column(JsonType)

    challenge: Mapped[CodingChallenge] = relationship(back_populates="submissions")
