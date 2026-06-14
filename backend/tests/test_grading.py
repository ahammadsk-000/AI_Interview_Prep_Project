"""Unit tests for the evaluation domain (rubric, STAR, graders)."""
from __future__ import annotations

from app.domain.evaluation.enums import GradingDimension, StarComponent
from app.domain.evaluation.grader import grade_answer, grade_behavioral
from app.domain.evaluation.rubric import score_rubric
from app.domain.evaluation.star import analyze_star

STRONG_BEHAVIORAL = (
    "In my previous role the situation was a failing checkout service. My task was to "
    "restore reliability. I led a small team: first I analyzed the root cause, then I "
    "implemented retries and caching with Redis. As a result we reduced errors by 60% "
    "and improved checkout success, and I owned the rollout end to end."
)
WEAK = "Um, I guess we did some stuff and it kind of worked out, you know."

STRONG_TECHNICAL = (
    "I would use a hash map to achieve O(n) lookups. First, I iterate the array, then for "
    "each element I check the complement. For example, with [2,7] and target 9 I return the "
    "indices. As a result the solution runs in linear time and constant extra space per step."
)


def test_rubric_scores_strong_higher_than_weak():
    assert score_rubric(STRONG_TECHNICAL).total > score_rubric(WEAK).total
    assert score_rubric("").total == 0


def test_star_detects_all_components():
    star = analyze_star(STRONG_BEHAVIORAL)
    assert star.components[StarComponent.SITUATION]
    assert star.components[StarComponent.TASK]
    assert star.components[StarComponent.ACTION]
    assert star.components[StarComponent.RESULT]
    assert star.score == 100
    assert star.missing == []


def test_star_flags_missing_on_weak_answer():
    star = analyze_star(WEAK)
    assert star.score < 100
    assert star.missing


def test_grade_answer_dimensions_and_feedback():
    grade = grade_answer(STRONG_TECHNICAL)
    assert 0 <= grade.total <= 100
    assert grade.score_out_of_10 == round(grade.total / 10, 1)
    assert set(grade.dimensions) == set(GradingDimension)
    assert grade.feedback

    weak = grade_answer(WEAK)
    assert weak.total < grade.total


def test_grade_behavioral_rewards_star_and_ownership():
    strong = grade_behavioral(STRONG_BEHAVIORAL)
    weak = grade_behavioral(WEAK)
    assert strong.total > weak.total
    assert strong.competencies  # all competencies present
    assert strong.star.score >= weak.star.score
