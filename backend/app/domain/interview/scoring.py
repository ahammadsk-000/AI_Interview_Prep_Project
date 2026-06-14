"""Lightweight, deterministic answer-signal scorer.

Used for *difficulty adaptation* during a live interview — not the full rubric
grading (that is Module 8 / Phase 5). Rewards substance, structure, specificity,
and technical vocabulary; penalizes empty or filler-only answers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.resume.analyzer import ACTION_VERBS
from app.domain.resume.skills import extract_skills

_FILLER = ("um", "uh", "like", "you know", "basically", "actually", "kind of", "sort of")
_STRUCTURE_CUES = (
    "first", "second", "then", "finally", "because", "therefore",
    "for example", "as a result", "trade-off", "tradeoff",
)
_NUMBER_RE = re.compile(r"\d+%|\$\s?\d+|\b\d+\b")


@dataclass
class AnswerSignal:
    score: int  # 0–100
    word_count: int
    technical_terms: int
    filler_count: int

    @property
    def is_strong(self) -> bool:
        return self.score >= 65

    @property
    def is_weak(self) -> bool:
        return self.score < 40


def score_answer(answer: str) -> AnswerSignal:
    text = (answer or "").strip()
    low = text.lower()
    words = text.split()
    wc = len(words)

    if wc == 0:
        return AnswerSignal(score=0, word_count=0, technical_terms=0, filler_count=0)

    # Length adequacy: ~60–220 words is a solid spoken answer.
    if wc < 15:
        length = wc / 15 * 50
    elif wc <= 220:
        length = 100
    else:
        length = max(70, 100 - (wc - 220) / 10)

    structure = min(100, sum(low.count(c) for c in _STRUCTURE_CUES) * 25)
    specificity = min(100, len(_NUMBER_RE.findall(text)) * 25)
    tech_terms = len(extract_skills(text))
    technical = min(100, tech_terms * 20)
    action = min(100, sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", low)) * 20)

    filler = sum(low.count(f) for f in _FILLER)
    filler_penalty = min(30, filler * 5)

    raw = (
        0.30 * length
        + 0.20 * structure
        + 0.20 * technical
        + 0.15 * specificity
        + 0.15 * action
    ) - filler_penalty
    score = max(0, min(100, round(raw)))
    return AnswerSignal(
        score=score, word_count=wc, technical_terms=tech_terms, filler_count=filler
    )
