"""Deterministic STAR-method detector (Situation · Task · Action · Result).

Detects which STAR components a behavioral answer covers, using cue phrases plus
structural signals (action verbs, quantified results). Heuristic but explainable —
flags the missing components that most weaken a behavioral answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain.evaluation.enums import StarComponent
from app.domain.interview.scoring import _NUMBER_RE  # reuse quantification regex
from app.domain.resume.analyzer import ACTION_VERBS

_CUES: dict[StarComponent, tuple[str, ...]] = {
    StarComponent.SITUATION: (
        "situation", "at the time", "when i was", "at my previous", "the context",
        "we had", "background", "the company", "the team was", "faced with",
    ),
    StarComponent.TASK: (
        "my task", "i was responsible", "the goal was", "i needed to", "my role was",
        "objective", "i was asked to", "challenge was", "we had to",
    ),
    StarComponent.ACTION: (
        "i decided", "i implemented", "i did", "first i", "then i", "i approached",
        "my approach", "i took", "to solve", "i worked",
    ),
    StarComponent.RESULT: (
        "as a result", "resulted in", "the outcome", "we achieved", "impact",
        "in the end", "ultimately", "this led to", "improved", "reduced",
    ),
}


@dataclass
class StarAnalysis:
    components: dict[StarComponent, bool]
    score: int  # 0–100
    missing: list[StarComponent] = field(default_factory=list)


def analyze_star(answer: str) -> StarAnalysis:
    text = answer or ""
    low = text.lower()

    present: dict[StarComponent, bool] = {}
    present[StarComponent.SITUATION] = any(c in low for c in _CUES[StarComponent.SITUATION])
    present[StarComponent.TASK] = any(c in low for c in _CUES[StarComponent.TASK])
    # Action: explicit cues OR several action verbs.
    action_verbs = sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", low))
    present[StarComponent.ACTION] = (
        any(c in low for c in _CUES[StarComponent.ACTION]) or action_verbs >= 2
    )
    # Result: explicit cues OR a quantified outcome.
    present[StarComponent.RESULT] = (
        any(c in low for c in _CUES[StarComponent.RESULT]) or bool(_NUMBER_RE.search(text))
    )

    covered = sum(1 for v in present.values() if v)
    score = round(covered / len(StarComponent) * 100)
    missing = [c for c, ok in present.items() if not ok]
    return StarAnalysis(components=present, score=score, missing=missing)
