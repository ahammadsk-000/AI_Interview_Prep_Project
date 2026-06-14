"""Deterministic rubric scorer for the four answer-grading dimensions.

Technical · Communication · Completeness · Confidence — each 0–100, derived from
explainable text signals. The LLM later adds prose (better/industry-standard
answers); these numbers are the reproducible backbone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.evaluation.enums import GradingDimension
from app.domain.resume.analyzer import ACTION_VERBS
from app.domain.resume.skills import extract_skills

_STRUCTURE_CUES = (
    "first", "second", "then", "finally", "because", "therefore",
    "for example", "as a result", "in summary", "however", "trade-off", "tradeoff",
)
_HEDGES = ("maybe", "i think", "i guess", "probably", "kind of", "sort of", "not sure", "i feel like")
_FILLER = ("um", "uh", "you know", "basically", "actually", "like,")
_NUMBER_RE = re.compile(r"\d+%|\$\s?\d+|\b\d+\b")
_CONCLUSION_CUES = ("in conclusion", "in summary", "overall", "to summarize", "as a result", "ultimately")


@dataclass
class RubricScores:
    dimensions: dict[GradingDimension, int]
    total: int  # weighted 0–100

    @property
    def out_of_10(self) -> float:
        return round(self.total / 10, 1)


_WEIGHTS = {
    GradingDimension.TECHNICAL: 0.30,
    GradingDimension.COMMUNICATION: 0.25,
    GradingDimension.COMPLETENESS: 0.25,
    GradingDimension.CONFIDENCE: 0.20,
}


def _clamp(v: float) -> int:
    return max(0, min(100, round(v)))


def score_rubric(answer: str) -> RubricScores:
    text = (answer or "").strip()
    low = text.lower()
    words = text.split()
    wc = len(words)

    if wc == 0:
        zero = dict.fromkeys(GradingDimension, 0)
        return RubricScores(dimensions=zero, total=0)

    # Technical: domain vocabulary density.
    tech_terms = len(extract_skills(text))
    technical = _clamp(tech_terms * 18)

    # Communication: structure + readable length − filler.
    structure = sum(low.count(c) for c in _STRUCTURE_CUES)
    filler = sum(low.count(f) for f in _FILLER)
    length_ok = 100 if 40 <= wc <= 260 else (wc / 40 * 100 if wc < 40 else 80)
    communication = _clamp(0.5 * min(100, structure * 25) + 0.5 * length_ok - filler * 4)

    # Completeness: length adequacy + a conclusion/result + specifics.
    has_conclusion = any(c in low for c in _CONCLUSION_CUES)
    specifics = min(100, len(_NUMBER_RE.findall(text)) * 25)
    completeness = _clamp(
        0.45 * min(100, wc / 120 * 100) + 0.30 * (100 if has_conclusion else 40) + 0.25 * specifics
    )

    # Confidence: ownership (action verbs, "I" statements) − hedging.
    action_verbs = sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", low))
    i_statements = len(re.findall(r"\bi\b", low))
    hedges = sum(low.count(h) for h in _HEDGES)
    confidence = _clamp(
        40 + min(40, action_verbs * 10) + min(20, i_statements * 3) - hedges * 8
    )

    dims = {
        GradingDimension.TECHNICAL: technical,
        GradingDimension.COMMUNICATION: communication,
        GradingDimension.COMPLETENESS: completeness,
        GradingDimension.CONFIDENCE: confidence,
    }
    total = _clamp(sum(dims[d] * w for d, w in _WEIGHTS.items()))
    return RubricScores(dimensions=dims, total=total)
