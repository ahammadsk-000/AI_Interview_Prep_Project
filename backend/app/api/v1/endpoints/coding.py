"""Coding Interview Platform + DSA Evaluation endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import ChallengeSvc, CurrentUser, SubmissionSvc, require_roles
from app.domain.identity.enums import RoleName
from app.models.coding import CodingChallenge, CodingSubmission, TestCase
from app.schemas.coding import (
    CaseResultPublic,
    ChallengeCreate,
    ChallengePublic,
    ChallengeSummary,
    RunRequest,
    SubmissionResultPublic,
    SubmitRequest,
    VisibleTestCase,
)
from app.services.coding_service import GradedRun

router = APIRouter(prefix="/coding", tags=["coding"])


def _challenge_public(challenge: CodingChallenge, cases: list[TestCase]) -> ChallengePublic:
    return ChallengePublic(
        id=challenge.id, slug=challenge.slug, title=challenge.title,
        difficulty=challenge.difficulty, prompt=challenge.prompt,
        entrypoint=challenge.entrypoint, starter_code=challenge.starter_code or {},
        tags=challenge.tags or [], is_public=challenge.is_public,
        visible_test_cases=[
            VisibleTestCase(args=tc.args or [], expected=(tc.expected_output or {}).get("value"))
            for tc in cases if not tc.is_hidden
        ],
        hidden_test_count=sum(1 for tc in cases if tc.is_hidden),
    )


def _result_from_run(run: GradedRun) -> SubmissionResultPublic:
    ev = run.evaluation
    cases = [
        CaseResultPublic(
            index=c.index, passed=c.passed, is_hidden=c.is_hidden,
            # Don't leak timing/error details for hidden cases.
            runtime_ms=None if c.is_hidden else c.runtime_ms,
            error=None if c.is_hidden else c.error,
        )
        for c in run.cases
    ]
    return SubmissionResultPublic(
        submission_id=run.submission_id, status=ev.status.value,
        passed=ev.passed, total=ev.total,
        correctness_score=ev.correctness_score, edge_case_score=ev.edge_case_score,
        code_quality_score=ev.code_quality_score, time_complexity=ev.time_complexity,
        space_complexity=ev.space_complexity, readiness_score=ev.readiness_score,
        difficulty_rating=ev.difficulty_rating, runtime_ms=ev.runtime_ms,
        suggestions=ev.suggestions, complexity_notes=ev.complexity_notes, cases=cases,
    )


# ── Challenges ──────────────────────────────────────────────────────
@router.post(
    "/challenges",
    response_model=ChallengePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.MENTOR))],
)
async def create_challenge(
    payload: ChallengeCreate, current: CurrentUser, challenges: ChallengeSvc
) -> ChallengePublic:
    challenge = await challenges.create(current.id, payload)
    cases = await challenges.test_cases(challenge.id)
    return _challenge_public(challenge, cases)


@router.get("/challenges", response_model=list[ChallengeSummary])
async def list_challenges(
    current: CurrentUser,
    challenges: ChallengeSvc,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ChallengeSummary]:
    records = await challenges.list_visible(current.id, limit=limit, offset=offset)
    return [
        ChallengeSummary(
            id=c.id, slug=c.slug, title=c.title, difficulty=c.difficulty, tags=c.tags or []
        )
        for c in records
    ]


@router.get("/challenges/{challenge_id}", response_model=ChallengePublic)
async def get_challenge(
    challenge_id: uuid.UUID, current: CurrentUser, challenges: ChallengeSvc
) -> ChallengePublic:
    challenge = await challenges.get_visible(challenge_id, current.id)
    cases = await challenges.test_cases(challenge_id)
    return _challenge_public(challenge, cases)


# ── Run / Submit ────────────────────────────────────────────────────
@router.post("/challenges/{challenge_id}/run", response_model=SubmissionResultPublic)
async def run_code(
    challenge_id: uuid.UUID, payload: RunRequest, current: CurrentUser, submissions: SubmissionSvc
) -> SubmissionResultPublic:
    return _result_from_run(await submissions.run(current.id, challenge_id, payload))


@router.post("/challenges/{challenge_id}/submit", response_model=SubmissionResultPublic)
async def submit_code(
    challenge_id: uuid.UUID, payload: SubmitRequest, current: CurrentUser,
    submissions: SubmissionSvc,
) -> SubmissionResultPublic:
    return _result_from_run(await submissions.submit(current.id, challenge_id, payload))


@router.get("/submissions/{submission_id}", response_model=SubmissionResultPublic)
async def get_submission(
    submission_id: uuid.UUID, current: CurrentUser, submissions: SubmissionSvc
) -> SubmissionResultPublic:
    sub: CodingSubmission = await submissions.get_owned_submission(submission_id, current.id)
    ev = sub.evaluation or {}
    return SubmissionResultPublic(
        submission_id=sub.id, status=sub.status.value, passed=sub.passed, total=sub.total,
        correctness_score=ev.get("correctness_score", 0),
        edge_case_score=ev.get("edge_case_score", 0),
        code_quality_score=ev.get("code_quality_score", 0),
        time_complexity=ev.get("time_complexity", "O(?)"),
        space_complexity=ev.get("space_complexity", "O(?)"),
        readiness_score=ev.get("readiness_score", 0),
        difficulty_rating=ev.get("difficulty_rating", "?"),
        runtime_ms=sub.runtime_ms,
        suggestions=ev.get("suggestions", []),
        complexity_notes=ev.get("complexity_notes", []),
        cases=[],
    )
