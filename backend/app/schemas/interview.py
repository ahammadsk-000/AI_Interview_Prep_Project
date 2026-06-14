"""Interview / Voice DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.interview.enums import (
    Difficulty,
    InterviewStatus,
    InterviewType,
    TurnRole,
)


class StartInterviewRequest(BaseModel):
    type: InterviewType
    difficulty: Difficulty = Difficulty.MEDIUM
    planned_questions: int = Field(default=5, ge=1, le=40)
    # Optional explicit focus skills; if omitted and use_resume is true, the
    # service derives skills from the candidate's most recent résumé.
    skills: list[str] | None = None
    use_resume: bool = True


class TurnPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: TurnRole
    content: str
    order_idx: int
    score: int | None = None


class SessionStatePublic(BaseModel):
    interview_id: uuid.UUID
    session_id: uuid.UUID
    type: InterviewType
    status: InterviewStatus
    current_difficulty: Difficulty
    planned_questions: int
    questions_asked: int
    current_question: str | None = None
    done: bool = False
    summary: str | None = None
    avg_score: int | None = None


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=20_000)


class TranscriptPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    speaker: TurnRole
    text: str
    order_idx: int
    confidence: float | None = None


class StartVoiceRequest(BaseModel):
    interview_session_id: uuid.UUID


class VoiceSessionPublic(BaseModel):
    id: uuid.UUID
    interview_session_id: uuid.UUID
    status: str
    created_at: datetime


class VoiceTurnResponse(BaseModel):
    transcript: str
    confidence: float
    next_question: str | None = None
    done: bool = False
    question_audio_b64: str | None = None
    summary: str | None = None
