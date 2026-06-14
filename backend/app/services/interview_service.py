"""Interview use-cases: start, answer (with difficulty adaptation), state, end.

Orchestrates the :class:`InterviewEngine` (LLM + bank fallback) and persistence.
Enforces per-user ownership (other users' sessions are reported as not found).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.ai.interview_engine import InterviewEngine, QATurn
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.interview.enums import InterviewStatus, TurnRole
from app.domain.interview.scoring import score_answer
from app.domain.resume.skills import extract_skills
from app.models.interview import Interview, InterviewSession
from app.repositories.interview import InterviewRepository
from app.repositories.resume import ResumeRepository
from app.schemas.interview import StartInterviewRequest


@dataclass
class SessionState:
    interview: Interview
    session: InterviewSession
    questions_asked: int
    current_question: str | None
    done: bool
    summary: str | None
    avg_score: int | None


class InterviewService:
    def __init__(
        self,
        repo: InterviewRepository,
        engine: InterviewEngine,
        resumes: ResumeRepository | None = None,
    ) -> None:
        self._repo = repo
        self._engine = engine
        self._resumes = resumes

    async def _resolve_skills(self, user_id: uuid.UUID, req: StartInterviewRequest) -> list[str]:
        """Explicit focus skills win; otherwise derive them from the latest résumé."""
        if req.skills:
            return sorted({s.strip() for s in req.skills if s.strip()})
        if req.use_resume and self._resumes is not None:
            resumes = await self._resumes.list_for_user(user_id, limit=1)
            if resumes and resumes[0].parsed_text:
                return sorted(extract_skills(resumes[0].parsed_text))
        return []

    @staticmethod
    def _session_skills(interview: Interview) -> list[str]:
        return list((interview.config or {}).get("skills", []))

    # ── ownership ────────────────────────────────────────────────────
    async def get_owned_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[InterviewSession, Interview]:
        session = await self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError("Interview session not found.")
        interview = await self._repo.get_interview(session.interview_id)
        if interview is None or interview.user_id != user_id:
            raise NotFoundError("Interview session not found.")
        return session, interview

    # ── history reconstruction ───────────────────────────────────────
    async def _history(self, session_id: uuid.UUID) -> tuple[list[QATurn], set[str], int]:
        turns = await self._repo.turns(session_id)
        history: list[QATurn] = []
        asked: set[str] = set()
        interviewer_count = 0
        for t in turns:
            if t.role == TurnRole.INTERVIEWER:
                history.append(QATurn(question=t.content))
                asked.add(t.content)
                interviewer_count += 1
            elif history:
                history[-1].answer = t.content
        return history, asked, interviewer_count

    # ── start ────────────────────────────────────────────────────────
    async def start(self, user_id: uuid.UUID, req: StartInterviewRequest) -> SessionState:
        skills = await self._resolve_skills(user_id, req)
        interview = await self._repo.add_interview(
            Interview(
                user_id=user_id, type=req.type, difficulty=req.difficulty,
                config={"skills": skills},
            )
        )
        session = await self._repo.add_session(
            InterviewSession(
                interview_id=interview.id,
                round=1,
                current_difficulty=req.difficulty,
                planned_questions=req.planned_questions,
            )
        )
        question = await self._engine.next_question(
            interview_type=req.type, difficulty=req.difficulty,
            history=[], asked=set(), last_signal=None, skills=skills,
        )
        await self._repo.add_turn(
            session.id, role=TurnRole.INTERVIEWER, content=question, order_idx=0
        )
        return SessionState(
            interview=interview, session=session, questions_asked=1,
            current_question=question, done=False, summary=None, avg_score=None,
        )

    # ── answer ───────────────────────────────────────────────────────
    async def submit_answer(
        self, user_id: uuid.UUID, session_id: uuid.UUID, answer: str
    ) -> SessionState:
        session, interview = await self.get_owned_session(session_id, user_id)
        if session.status != InterviewStatus.ACTIVE:
            raise ValidationError("This interview session is already completed.")

        history, asked, interviewer_count = await self._history(session_id)
        if interviewer_count == 0:
            raise ValidationError("No question has been asked yet.")

        signal = score_answer(answer)
        idx = await self._repo.next_order_idx(session_id)
        await self._repo.add_turn(
            session_id, role=TurnRole.CANDIDATE, content=answer,
            order_idx=idx, score=signal.score,
        )
        if history:
            history[-1].answer = answer

        session.current_difficulty = self._engine_adapt(session.current_difficulty, signal)

        if interviewer_count < session.planned_questions:
            question = await self._engine.next_question(
                interview_type=interview.type,
                difficulty=session.current_difficulty,
                history=history, asked=asked, last_signal=signal,
                skills=self._session_skills(interview),
            )
            await self._repo.add_turn(
                session_id, role=TurnRole.INTERVIEWER, content=question, order_idx=idx + 1
            )
            return SessionState(
                interview=interview, session=session,
                questions_asked=interviewer_count + 1,
                current_question=question, done=False, summary=None, avg_score=None,
            )

        # Final question answered → finalize.
        avg = await self._repo.candidate_avg_score(session_id)
        avg_int = round(float(avg)) if avg is not None else None
        summary = await self._engine.summarize(history, avg_int or 0)
        session.avg_score = float(avg_int) if avg_int is not None else None
        session.summary = summary
        session.status = InterviewStatus.COMPLETED
        interview.status = InterviewStatus.COMPLETED
        return SessionState(
            interview=interview, session=session, questions_asked=interviewer_count,
            current_question=None, done=True, summary=summary, avg_score=avg_int,
        )

    @staticmethod
    def _engine_adapt(current, signal):
        from app.ai.interview_engine import adapt_difficulty

        return adapt_difficulty(current, signal)

    # ── state ────────────────────────────────────────────────────────
    async def get_state(self, user_id: uuid.UUID, session_id: uuid.UUID) -> SessionState:
        session, interview = await self.get_owned_session(session_id, user_id)
        turns = await self._repo.turns(session_id)
        interviewer = [t for t in turns if t.role == TurnRole.INTERVIEWER]
        current = interviewer[-1].content if interviewer else None
        done = session.status != InterviewStatus.ACTIVE
        avg = round(session.avg_score) if session.avg_score is not None else None
        return SessionState(
            interview=interview, session=session,
            questions_asked=len(interviewer),
            current_question=None if done else current,
            done=done, summary=session.summary, avg_score=avg,
        )

    # ── end ──────────────────────────────────────────────────────────
    async def end(self, user_id: uuid.UUID, session_id: uuid.UUID) -> SessionState:
        session, interview = await self.get_owned_session(session_id, user_id)
        if session.status == InterviewStatus.ACTIVE:
            history, _, _ = await self._history(session_id)
            avg = await self._repo.candidate_avg_score(session_id)
            avg_int = round(float(avg)) if avg is not None else None
            session.summary = await self._engine.summarize(history, avg_int or 0)
            session.avg_score = float(avg_int) if avg_int is not None else None
            session.status = InterviewStatus.COMPLETED
            interview.status = InterviewStatus.COMPLETED
        return await self.get_state(user_id, session_id)
