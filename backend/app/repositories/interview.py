"""SQLAlchemy repositories for the Interview and Voice contexts."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interview.enums import TurnRole
from app.models.interview import (
    Interview,
    InterviewSession,
    Recording,
    Transcript,
    Turn,
    VoiceSession,
)


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_interview(self, interview: Interview) -> Interview:
        self._s.add(interview)
        await self._s.flush()
        await self._s.refresh(interview, attribute_names=["created_at", "updated_at"])
        return interview

    async def add_session(self, session: InterviewSession) -> InterviewSession:
        self._s.add(session)
        await self._s.flush()
        await self._s.refresh(session, attribute_names=["created_at", "updated_at"])
        return session

    async def get_interview(self, id_: uuid.UUID) -> Interview | None:
        return await self._s.get(Interview, id_)

    async def get_session(self, id_: uuid.UUID) -> InterviewSession | None:
        return await self._s.get(InterviewSession, id_)

    async def add_turn(
        self, session_id: uuid.UUID, *, role: TurnRole, content: str,
        order_idx: int, score: int | None = None, audio_key: str | None = None,
    ) -> Turn:
        turn = Turn(
            session_id=session_id, role=role, content=content,
            order_idx=order_idx, score=score, audio_key=audio_key,
        )
        self._s.add(turn)
        await self._s.flush()
        return turn

    async def turns(self, session_id: uuid.UUID) -> list[Turn]:
        stmt = (
            select(Turn).where(Turn.session_id == session_id).order_by(Turn.order_idx)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def next_order_idx(self, session_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Turn).where(Turn.session_id == session_id)
        return int((await self._s.execute(stmt)).scalar_one())

    async def candidate_avg_score(self, session_id: uuid.UUID) -> float | None:
        stmt = (
            select(func.avg(Turn.score))
            .where(Turn.session_id == session_id, Turn.role == TurnRole.CANDIDATE)
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()


class VoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_voice_session(self, vs: VoiceSession) -> VoiceSession:
        self._s.add(vs)
        await self._s.flush()
        await self._s.refresh(vs, attribute_names=["created_at", "updated_at"])
        return vs

    async def get_voice_session(self, id_: uuid.UUID) -> VoiceSession | None:
        return await self._s.get(VoiceSession, id_)

    async def add_transcript(
        self, voice_session_id: uuid.UUID, *, speaker: TurnRole, text: str,
        order_idx: int, confidence: float | None = None,
    ) -> Transcript:
        t = Transcript(
            voice_session_id=voice_session_id, speaker=speaker, text=text,
            order_idx=order_idx, confidence=confidence,
        )
        self._s.add(t)
        await self._s.flush()
        return t

    async def add_recording(
        self, voice_session_id: uuid.UUID, *, speaker: TurnRole,
        storage_key: str, duration_ms: int | None = None,
    ) -> Recording:
        r = Recording(
            voice_session_id=voice_session_id, speaker=speaker,
            storage_key=storage_key, duration_ms=duration_ms,
        )
        self._s.add(r)
        await self._s.flush()
        return r

    async def transcripts(self, voice_session_id: uuid.UUID) -> list[Transcript]:
        stmt = (
            select(Transcript)
            .where(Transcript.voice_session_id == voice_session_id)
            .order_by(Transcript.order_idx)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def next_transcript_idx(self, voice_session_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Transcript)
            .where(Transcript.voice_session_id == voice_session_id)
        )
        return int((await self._s.execute(stmt)).scalar_one())
