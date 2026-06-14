"""Interview / Voice ORM models (Phase 3).

Bounded contexts: Interview and Voice. An ``Interview`` aggregates one or more
``InterviewSession`` rounds; each session is an ordered list of ``Turn`` rows. A
``VoiceSession`` overlays an interview session with transcripts and recordings.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, uuid_pk
from app.domain.interview.enums import (
    Difficulty,
    InterviewStatus,
    InterviewType,
    TurnRole,
    VoiceSessionStatus,
)
from app.models.user import JsonType, _enum


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[InterviewType] = mapped_column(_enum(InterviewType, "interview_type"))
    difficulty: Mapped[Difficulty] = mapped_column(
        _enum(Difficulty, "interview_difficulty"), default=Difficulty.MEDIUM
    )
    status: Mapped[InterviewStatus] = mapped_column(
        _enum(InterviewStatus, "interview_status"),
        default=InterviewStatus.ACTIVE,
        nullable=False,
    )
    config: Mapped[dict | None] = mapped_column(JsonType)

    sessions: Mapped[list[InterviewSession]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_difficulty: Mapped[Difficulty] = mapped_column(
        _enum(Difficulty, "session_difficulty"), default=Difficulty.MEDIUM
    )
    planned_questions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        _enum(InterviewStatus, "session_status"),
        default=InterviewStatus.ACTIVE,
        nullable=False,
    )
    avg_score: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)

    interview: Mapped[Interview] = relationship(back_populates="sessions")
    turns: Mapped[list[Turn]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    role: Mapped[TurnRole] = mapped_column(_enum(TurnRole, "turn_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)  # answer-signal (candidate turns)
    audio_key: Mapped[str | None] = mapped_column(String(512))

    session: Mapped[InterviewSession] = relationship(back_populates="turns")


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    status: Mapped[VoiceSessionStatus] = mapped_column(
        _enum(VoiceSessionStatus, "voice_session_status"),
        default=VoiceSessionStatus.ACTIVE,
        nullable=False,
    )
    provider: Mapped[str | None] = mapped_column(String(64))

    transcripts: Mapped[list[Transcript]] = relationship(
        back_populates="voice_session", cascade="all, delete-orphan"
    )
    recordings: Mapped[list[Recording]] = relationship(
        back_populates="voice_session", cascade="all, delete-orphan"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = uuid_pk()
    voice_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("voice_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    speaker: Mapped[TurnRole] = mapped_column(_enum(TurnRole, "transcript_speaker"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)

    voice_session: Mapped[VoiceSession] = relationship(back_populates="transcripts")


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = uuid_pk()
    voice_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("voice_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    speaker: Mapped[TurnRole] = mapped_column(_enum(TurnRole, "recording_speaker"))
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    voice_session: Mapped[VoiceSession] = relationship(back_populates="recordings")
