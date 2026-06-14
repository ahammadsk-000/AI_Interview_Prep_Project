"""DSA Evaluation Engine — combines execution + static analysis into a verdict.

Produces correctness, time/space complexity estimates, code-quality, edge-case
coverage, an overall interview-readiness score, a difficulty rating, and concrete
improvement suggestions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.execution.base import ExecutionResult
from app.domain.coding.complexity import estimate
from app.domain.coding.enums import (
    ChallengeDifficulty,
    ComplexityClass,
    Language,
    SubmissionStatus,
)
from app.domain.coding.quality import assess


@dataclass
class CodingEvaluation:
    status: SubmissionStatus
    correctness_score: int
    edge_case_score: int
    code_quality_score: int
    time_complexity: str
    space_complexity: str
    readiness_score: int
    difficulty_rating: str
    passed: int
    total: int
    runtime_ms: float | None
    suggestions: list[str] = field(default_factory=list)
    complexity_notes: list[str] = field(default_factory=list)


_DIFF_EXPECTATION = {
    ChallengeDifficulty.EASY: ComplexityClass.O_N,
    ChallengeDifficulty.MEDIUM: ComplexityClass.O_N_LOG_N,
    ChallengeDifficulty.HARD: ComplexityClass.O_N2,
}


def evaluate(
    *,
    source: str,
    language: Language,
    entrypoint: str,
    difficulty: ChallengeDifficulty,
    execution: ExecutionResult,
) -> CodingEvaluation:
    total = execution.total
    passed = execution.passed
    correctness = round(passed / total * 100) if total else 0

    hidden = [c for c in execution.cases if c.is_hidden]
    hidden_passed = sum(1 for c in hidden if c.passed)
    edge_case = round(hidden_passed / len(hidden) * 100) if hidden else correctness

    comp = estimate(source, language, entrypoint)
    qual = assess(source, language)

    # Complexity quality: reward meeting the difficulty's expected bound.
    expected = _DIFF_EXPECTATION[difficulty]
    if comp.time == ComplexityClass.UNKNOWN:
        complexity_quality = 60
    elif comp.time.rank <= expected.rank:
        complexity_quality = 100
    elif comp.time.rank == expected.rank + 1:
        complexity_quality = 70
    else:
        complexity_quality = 40

    # Interview readiness: correctness dominates, then complexity, edge cases, style.
    readiness = round(
        0.45 * correctness
        + 0.20 * complexity_quality
        + 0.20 * edge_case
        + 0.15 * qual.score
    )

    suggestions = _suggestions(execution, comp, qual, complexity_quality, expected)

    return CodingEvaluation(
        status=execution.status,
        correctness_score=correctness,
        edge_case_score=edge_case,
        code_quality_score=qual.score,
        time_complexity=comp.time.value,
        space_complexity=comp.space.value,
        readiness_score=readiness,
        difficulty_rating=difficulty.value,
        passed=passed,
        total=total,
        runtime_ms=execution.runtime_ms,
        suggestions=suggestions,
        complexity_notes=comp.notes,
    )


def _suggestions(execution, comp, qual, complexity_quality, expected) -> list[str]:
    out: list[str] = []
    if execution.status == SubmissionStatus.COMPILE_ERROR:
        out.append("Fix the compile/parse error before resubmitting.")
    elif execution.status == SubmissionStatus.TIME_LIMIT:
        out.append("Your solution timed out — reduce its time complexity or remove infinite loops.")
    elif execution.passed < execution.total:
        failed = execution.total - execution.passed
        out.append(f"{failed} test case(s) failed — revisit edge cases and boundary conditions.")
    if complexity_quality < 70:
        out.append(
            f"Estimated time complexity is {comp.time.value}; aim for {expected.value} "
            "or better for this difficulty."
        )
    out.extend(comp.notes)
    out.extend(qual.notes[:3])
    if not out:
        out.append("Solid solution — correct, efficient, and clean.")
    return out
