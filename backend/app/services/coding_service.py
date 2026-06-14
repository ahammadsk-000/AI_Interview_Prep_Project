"""Coding platform use-cases: challenge authoring + run/submit + DSA evaluation.

``run`` executes against visible tests for quick feedback (no persistence);
``submit`` executes the full suite (incl. hidden cases), evaluates, and persists.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.ai.execution.base import ExecutionEngine, ExecutionRequest, TestCaseSpec
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.domain.coding.evaluator import CodingEvaluation, evaluate
from app.models.coding import CodingChallenge, CodingSubmission, TestCase
from app.repositories.coding import ChallengeRepository, SubmissionRepository
from app.schemas.coding import ChallengeCreate, RunRequest


@dataclass
class GradedRun:
    evaluation: CodingEvaluation
    cases: list  # CaseResult from execution
    submission_id: uuid.UUID | None


class ChallengeService:
    def __init__(self, repo: ChallengeRepository) -> None:
        self._repo = repo

    async def create(self, creator_id: uuid.UUID, data: ChallengeCreate) -> CodingChallenge:
        if await self._repo.slug_exists(data.slug):
            raise ConflictError(f"A challenge with slug '{data.slug}' already exists.")
        challenge = CodingChallenge(
            slug=data.slug, title=data.title, difficulty=data.difficulty,
            prompt=data.prompt, entrypoint=data.entrypoint,
            starter_code=data.starter_code or {}, tags=data.tags or [],
            is_public=data.is_public, created_by=creator_id,
            test_cases=[
                TestCase(
                    order_idx=i, args=tc.args,
                    expected_output={"value": tc.expected},
                    is_hidden=tc.is_hidden, weight=tc.weight,
                )
                for i, tc in enumerate(data.test_cases)
            ],
        )
        return await self._repo.add(challenge)

    async def get_visible(self, challenge_id: uuid.UUID, user_id: uuid.UUID) -> CodingChallenge:
        challenge = await self._repo.get(challenge_id)
        if challenge is None or not (challenge.is_public or challenge.created_by == user_id):
            raise NotFoundError("Challenge not found.")
        return challenge

    async def list_visible(self, user_id: uuid.UUID, **kw):
        return await self._repo.list_visible(user_id, **kw)

    async def test_cases(self, challenge_id: uuid.UUID) -> list[TestCase]:
        return await self._repo.test_cases(challenge_id)


def _to_specs(cases: list[TestCase], *, only_visible: bool) -> list[TestCaseSpec]:
    specs: list[TestCaseSpec] = []
    for tc in cases:
        if only_visible and tc.is_hidden:
            continue
        specs.append(
            TestCaseSpec(
                index=tc.order_idx, args=tc.args or [],
                expected=(tc.expected_output or {}).get("value"),
                is_hidden=tc.is_hidden, weight=tc.weight,
            )
        )
    return specs


class SubmissionService:
    def __init__(
        self,
        challenges: ChallengeService,
        submissions: SubmissionRepository,
        engine: ExecutionEngine,
    ) -> None:
        self._challenges = challenges
        self._submissions = submissions
        self._engine = engine

    async def _grade(
        self, challenge: CodingChallenge, req: RunRequest, *, only_visible: bool
    ) -> tuple[CodingEvaluation, list]:
        cases = await self._challenges.test_cases(challenge.id)
        specs = _to_specs(cases, only_visible=only_visible)
        result = await self._engine.execute(
            ExecutionRequest(
                language=req.language, source=req.source, entrypoint=challenge.entrypoint,
                cases=specs, timeout_sec=settings.CODE_EXEC_TIMEOUT_SEC,
            )
        )
        evaluation = evaluate(
            source=req.source, language=req.language, entrypoint=challenge.entrypoint,
            difficulty=challenge.difficulty, execution=result,
        )
        return evaluation, result.cases

    async def run(
        self, user_id: uuid.UUID, challenge_id: uuid.UUID, req: RunRequest
    ) -> GradedRun:
        challenge = await self._challenges.get_visible(challenge_id, user_id)
        evaluation, cases = await self._grade(challenge, req, only_visible=True)
        return GradedRun(evaluation=evaluation, cases=cases, submission_id=None)

    async def submit(
        self, user_id: uuid.UUID, challenge_id: uuid.UUID, req: RunRequest
    ) -> GradedRun:
        challenge = await self._challenges.get_visible(challenge_id, user_id)
        evaluation, cases = await self._grade(challenge, req, only_visible=False)
        submission = await self._submissions.add(
            CodingSubmission(
                user_id=user_id, challenge_id=challenge.id, language=req.language,
                source=req.source, status=evaluation.status,
                passed=evaluation.passed, total=evaluation.total,
                runtime_ms=evaluation.runtime_ms,
                evaluation={
                    "correctness_score": evaluation.correctness_score,
                    "edge_case_score": evaluation.edge_case_score,
                    "code_quality_score": evaluation.code_quality_score,
                    "time_complexity": evaluation.time_complexity,
                    "space_complexity": evaluation.space_complexity,
                    "readiness_score": evaluation.readiness_score,
                    "difficulty_rating": evaluation.difficulty_rating,
                    "suggestions": evaluation.suggestions,
                    "complexity_notes": evaluation.complexity_notes,
                },
            )
        )
        return GradedRun(evaluation=evaluation, cases=cases, submission_id=submission.id)

    async def get_owned_submission(
        self, submission_id: uuid.UUID, user_id: uuid.UUID
    ) -> CodingSubmission:
        sub = await self._submissions.get(submission_id)
        if sub is None or sub.user_id != user_id:
            raise NotFoundError("Submission not found.")
        return sub
