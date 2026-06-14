"""Answer grading + behavioral evaluation (deterministic cores).

These produce reproducible numeric scores and rule-based feedback. The service
layer enriches them with LLM-written prose (a better answer, an industry-standard
answer, a recruiter perspective) behind the ``LLMProvider`` port, with deterministic
fallbacks when no model is available.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.evaluation.enums import BehavioralCompetency, GradingDimension
from app.domain.evaluation.rubric import RubricScores, score_rubric
from app.domain.evaluation.star import StarAnalysis, analyze_star


@dataclass
class AnswerGrade:
    total: int
    score_out_of_10: float
    dimensions: dict[GradingDimension, int]
    feedback: list[str] = field(default_factory=list)


@dataclass
class BehavioralGrade:
    total: int
    competencies: dict[BehavioralCompetency, int]
    star: StarAnalysis
    feedback: list[str] = field(default_factory=list)


# ── Answer grading ──────────────────────────────────────────────────
def grade_answer(answer: str) -> AnswerGrade:
    rubric: RubricScores = score_rubric(answer)
    feedback = _answer_feedback(rubric)
    return AnswerGrade(
        total=rubric.total,
        score_out_of_10=rubric.out_of_10,
        dimensions=rubric.dimensions,
        feedback=feedback,
    )


def _answer_feedback(rubric: RubricScores) -> list[str]:
    out: list[str] = []
    d = rubric.dimensions
    if d[GradingDimension.TECHNICAL] < 50:
        out.append("Add concrete technical detail — name the tools, methods, and trade-offs.")
    if d[GradingDimension.COMMUNICATION] < 50:
        out.append("Structure the answer (point → reason → example) and trim filler words.")
    if d[GradingDimension.COMPLETENESS] < 50:
        out.append("Finish with the outcome/impact so the answer feels complete.")
    if d[GradingDimension.CONFIDENCE] < 50:
        out.append("Speak with ownership — fewer hedges ('I think', 'maybe'), more 'I did X'.")
    if not out:
        out.append("Strong, well-rounded answer across all dimensions.")
    return out


# ── Behavioral evaluation ───────────────────────────────────────────
_LEADERSHIP = ("led", "mentored", "drove", "coordinated", "spearheaded", "guided", "owned the")
_OWNERSHIP = ("i took", "responsible", "accountable", "i ensured", "i owned", "took the initiative")
_TEAMWORK = ("we ", "collaborat", "partnered", "together", "cross-functional", "the team", "stakeholders")
_PROBLEM = ("analyzed", "root cause", "debugged", "trade-off", "tradeoff", "approach",
            "solved", "evaluated options")


def _competency(low: str, cues: tuple[str, ...], base: int = 30) -> int:
    hits = sum(low.count(c) for c in cues)
    return max(0, min(100, base + hits * 18))


def grade_behavioral(answer: str) -> BehavioralGrade:
    star = analyze_star(answer)
    low = (answer or "").lower()
    rubric = score_rubric(answer)

    competencies = {
        BehavioralCompetency.STAR: star.score,
        BehavioralCompetency.COMMUNICATION: rubric.dimensions[GradingDimension.COMMUNICATION],
        BehavioralCompetency.LEADERSHIP: _competency(low, _LEADERSHIP),
        BehavioralCompetency.OWNERSHIP: _competency(low, _OWNERSHIP),
        BehavioralCompetency.TEAMWORK: _competency(low, _TEAMWORK),
        BehavioralCompetency.PROBLEM_SOLVING: _competency(low, _PROBLEM),
    }
    # STAR coverage is weighted heavily for behavioral answers.
    total = max(0, min(100, round(
        0.35 * competencies[BehavioralCompetency.STAR]
        + 0.13 * competencies[BehavioralCompetency.COMMUNICATION]
        + 0.13 * competencies[BehavioralCompetency.LEADERSHIP]
        + 0.13 * competencies[BehavioralCompetency.OWNERSHIP]
        + 0.13 * competencies[BehavioralCompetency.TEAMWORK]
        + 0.13 * competencies[BehavioralCompetency.PROBLEM_SOLVING]
    )))
    feedback = _behavioral_feedback(star, competencies)
    return BehavioralGrade(total=total, competencies=competencies, star=star, feedback=feedback)


def _behavioral_feedback(star: StarAnalysis, competencies) -> list[str]:
    out: list[str] = []
    if star.missing:
        names = ", ".join(c.value for c in star.missing)
        out.append(f"Strengthen the STAR structure — your answer is light on: {names}.")
    if competencies[BehavioralCompetency.OWNERSHIP] < 50:
        out.append("Show personal ownership ('I decided/ensured…'), not just team activity.")
    if competencies[BehavioralCompetency.PROBLEM_SOLVING] < 50:
        out.append("Explain your reasoning and the trade-offs you weighed.")
    if not out:
        out.append("Well-structured behavioral answer with clear ownership and impact.")
    return out
