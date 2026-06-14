"""AI Answer Grading + Behavioral Evaluation + session feedback reports."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, GradingSvc
from app.schemas.evaluation import (
    AnswerGradePublic,
    BehavioralGradePublic,
    BehavioralRequest,
    GradeAnswerRequest,
    ScorePublic,
    SessionReportPublic,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/answer", response_model=AnswerGradePublic)
async def grade_answer(
    payload: GradeAnswerRequest, current: CurrentUser, grading: GradingSvc
) -> AnswerGradePublic:
    res = await grading.grade_answer(
        current.id, question=payload.question, answer=payload.answer,
        subject_id=payload.subject_id,
    )
    return AnswerGradePublic(
        score_id=res.score_id,
        total=res.grade.total,
        score_out_of_10=res.grade.score_out_of_10,
        dimensions={d.value: v for d, v in res.grade.dimensions.items()},
        feedback=res.grade.feedback,
        suggested_better_answer=res.better,
        industry_standard_answer=res.industry,
    )


@router.post("/behavioral", response_model=BehavioralGradePublic)
async def grade_behavioral(
    payload: BehavioralRequest, current: CurrentUser, grading: GradingSvc
) -> BehavioralGradePublic:
    res = await grading.grade_behavioral(
        current.id, question=payload.question, answer=payload.answer,
        subject_id=payload.subject_id,
    )
    g = res.grade
    return BehavioralGradePublic(
        score_id=res.score_id,
        behavioral_score=g.total,
        competencies={c.value: v for c, v in g.competencies.items()},
        star_components={c.value: ok for c, ok in g.star.components.items()},
        missing_star=[c.value for c in g.star.missing],
        feedback=g.feedback,
        recruiter_perspective=res.recruiter,
    )


@router.post("/sessions/{session_id}/grade", response_model=SessionReportPublic)
async def grade_session(
    session_id: uuid.UUID, current: CurrentUser, grading: GradingSvc
) -> SessionReportPublic:
    report, per_question = await grading.grade_session(current.id, session_id)
    return SessionReportPublic(
        report_id=report.id,
        interview_session_id=session_id,
        overall_score=report.overall_score,
        graded_answers=len(per_question),
        summary=report.summary or "",
        strengths=report.strengths or [],
        improvements=report.improvements or [],
        per_question=per_question,
    )


@router.get("/scores", response_model=list[ScorePublic])
async def list_scores(
    current: CurrentUser,
    grading: GradingSvc,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ScorePublic]:
    records = await grading.list_scores(current.id, limit=limit, offset=offset)
    return [
        ScorePublic(
            id=s.id, subject_type=s.subject_type, subject_id=s.subject_id,
            question=s.question, total=s.total, breakdown=s.breakdown or {},
            created_at=s.created_at,
        )
        for s in records
    ]


@router.get("/scores/{score_id}", response_model=ScorePublic)
async def get_score(
    score_id: uuid.UUID, current: CurrentUser, grading: GradingSvc
) -> ScorePublic:
    s = await grading.get_owned_score(score_id, current.id)
    return ScorePublic(
        id=s.id, subject_type=s.subject_type, subject_id=s.subject_id,
        question=s.question, total=s.total, breakdown=s.breakdown or {},
        created_at=s.created_at,
    )
