"""Evaluation use-cases: AI answer grading, behavioral evaluation, session reports.

Deterministic scores (rubric/STAR) are computed in the domain layer; this service
adds LLM-written prose (better/industry answers, recruiter perspective) and persists
``Score`` / ``FeedbackReport`` aggregates. Ownership is enforced via the interview
service for session-level reports.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.ai.grading import better_answer, industry_standard_answer, recruiter_perspective
from app.ai.llm.base import LLMProvider
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.evaluation.enums import SubjectType
from app.domain.evaluation.grader import (
    AnswerGrade,
    BehavioralGrade,
    grade_answer,
    grade_behavioral,
)
from app.domain.interview.enums import TurnRole
from app.models.evaluation import FeedbackReport, Score
from app.repositories.evaluation import FeedbackReportRepository, ScoreRepository
from app.services.interview_service import InterviewService


@dataclass
class AnswerGradeResult:
    grade: AnswerGrade
    better: str
    industry: str
    score_id: uuid.UUID | None


@dataclass
class BehavioralResult:
    grade: BehavioralGrade
    recruiter: str
    score_id: uuid.UUID | None


def _dims_json(grade: AnswerGrade) -> dict[str, int]:
    return {d.value: v for d, v in grade.dimensions.items()}


class GradingService:
    def __init__(
        self,
        scores: ScoreRepository,
        reports: FeedbackReportRepository,
        llm: LLMProvider,
        interviews: InterviewService,
    ) -> None:
        self._scores = scores
        self._reports = reports
        self._llm = llm
        self._interviews = interviews

    # ── Answer grading (Module 8) ────────────────────────────────────
    async def grade_answer(
        self, user_id: uuid.UUID, *, question: str | None, answer: str,
        subject_id: uuid.UUID | None = None, persist: bool = True,
    ) -> AnswerGradeResult:
        grade = grade_answer(answer)
        q = question or "the interview question"
        better = await better_answer(self._llm, q, answer, grade.feedback)
        industry = await industry_standard_answer(self._llm, q)

        score_id = None
        if persist:
            score = await self._scores.add(
                Score(
                    user_id=user_id, subject_type=SubjectType.ANSWER, subject_id=subject_id,
                    question=question, answer=answer, total=grade.total,
                    breakdown={"dimensions": _dims_json(grade),
                               "score_out_of_10": grade.score_out_of_10},
                    feedback={"feedback": grade.feedback, "better_answer": better,
                              "industry_standard": industry},
                )
            )
            score_id = score.id
        return AnswerGradeResult(grade=grade, better=better, industry=industry, score_id=score_id)

    # ── Behavioral evaluation (Module 9) ─────────────────────────────
    async def grade_behavioral(
        self, user_id: uuid.UUID, *, question: str | None, answer: str,
        subject_id: uuid.UUID | None = None,
    ) -> BehavioralResult:
        grade = grade_behavioral(answer)
        q = question or "the behavioral question"
        recruiter = await recruiter_perspective(self._llm, q, answer, grade.total)
        score = await self._scores.add(
            Score(
                user_id=user_id, subject_type=SubjectType.BEHAVIORAL, subject_id=subject_id,
                question=question, answer=answer, total=grade.total,
                breakdown={
                    "competencies": {c.value: v for c, v in grade.competencies.items()},
                    "star": {c.value: ok for c, ok in grade.star.components.items()},
                },
                feedback={"feedback": grade.feedback, "recruiter_perspective": recruiter},
            )
        )
        return BehavioralResult(grade=grade, recruiter=recruiter, score_id=score.id)

    # ── Session report (Module 8 + interview report generation) ──────
    async def grade_session(self, user_id: uuid.UUID, session_id: uuid.UUID):
        await self._interviews.get_owned_session(session_id, user_id)
        turns = await self._interviews._repo.turns(session_id)

        pairs: list[tuple[str, str, uuid.UUID]] = []
        pending_q: str | None = None
        for t in turns:
            if t.role == TurnRole.INTERVIEWER:
                pending_q = t.content
            elif t.role == TurnRole.CANDIDATE and pending_q is not None:
                pairs.append((pending_q, t.content, t.id))
                pending_q = None
        if not pairs:
            raise ValidationError("No answered questions to grade in this session.")

        per_question: list[dict] = []
        totals: list[int] = []
        dim_sums: dict[str, list[int]] = {}
        for question, answer, turn_id in pairs:
            grade = grade_answer(answer)
            totals.append(grade.total)
            dims = _dims_json(grade)
            for k, v in dims.items():
                dim_sums.setdefault(k, []).append(v)
            await self._scores.add(
                Score(
                    user_id=user_id, subject_type=SubjectType.ANSWER, subject_id=turn_id,
                    question=question, answer=answer, total=grade.total,
                    breakdown={"dimensions": dims, "score_out_of_10": grade.score_out_of_10},
                    feedback={"feedback": grade.feedback},
                )
            )
            per_question.append({
                "question": question, "score": grade.total,
                "score_out_of_10": grade.score_out_of_10, "feedback": grade.feedback,
            })

        overall = round(sum(totals) / len(totals))
        dim_avg = {k: round(sum(v) / len(v)) for k, v in dim_sums.items()}
        strengths = [f"{k.title()} ({s}/100)" for k, s in dim_avg.items() if s >= 70]
        improvements = [
            f"Improve {k} (currently {s}/100)." for k, s in dim_avg.items() if s < 55
        ]
        summary = (
            f"Graded {len(pairs)} answer(s); overall readiness {overall}/100. "
            + ("Strong areas: " + ", ".join(strengths) + ". " if strengths else "")
            + ("Focus next on: " + ", ".join(k for k, s in dim_avg.items() if s < 55) + "."
               if improvements else "Consistent performance across dimensions.")
        )
        report = await self._reports.add(
            FeedbackReport(
                user_id=user_id, interview_session_id=session_id, overall_score=overall,
                summary=summary, strengths=strengths, improvements=improvements,
                detail={"per_question": per_question, "dimension_averages": dim_avg},
            )
        )
        return report, per_question

    # ── Retrieval ────────────────────────────────────────────────────
    async def get_owned_score(self, score_id: uuid.UUID, user_id: uuid.UUID) -> Score:
        score = await self._scores.get(score_id)
        if score is None or score.user_id != user_id:
            raise NotFoundError("Score not found.")
        return score

    async def list_scores(self, user_id: uuid.UUID, **kw):
        return await self._scores.list_for_user(user_id, **kw)
