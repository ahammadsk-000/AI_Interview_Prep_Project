"""Unit tests for the interview engine internals (no DB, Stub LLM)."""
from __future__ import annotations

import pytest

from app.ai.interview_engine import InterviewEngine, QATurn, adapt_difficulty
from app.ai.llm.providers import StubProvider
from app.domain.interview.enums import Difficulty, InterviewType
from app.domain.interview.scoring import score_answer

STRONG_ANSWER = (
    "First, I led the redesign of our payments service in Python and FastAPI. "
    "I reduced p99 latency by 40% and increased throughput 3x by adding Redis caching "
    "and Kubernetes autoscaling. As a result, we cut incident rate significantly."
)
WEAK_ANSWER = "Um, I guess I did some stuff, you know, basically."


def test_score_answer_strong_vs_weak():
    assert score_answer(STRONG_ANSWER).is_strong
    assert score_answer(WEAK_ANSWER).is_weak
    assert score_answer("").score == 0


def test_adapt_difficulty_moves_with_signal():
    assert adapt_difficulty(Difficulty.MEDIUM, score_answer(STRONG_ANSWER)) == Difficulty.HARD
    assert adapt_difficulty(Difficulty.MEDIUM, score_answer(WEAK_ANSWER)) == Difficulty.EASY
    # Bounds: cannot go past HARD/EASY.
    assert adapt_difficulty(Difficulty.HARD, score_answer(STRONG_ANSWER)) == Difficulty.HARD
    assert adapt_difficulty(Difficulty.EASY, score_answer(WEAK_ANSWER)) == Difficulty.EASY


@pytest.mark.asyncio
async def test_engine_fallback_never_repeats():
    engine = InterviewEngine(StubProvider())
    asked: set[str] = set()
    history: list[QATurn] = []
    for _ in range(6):
        q = await engine.next_question(
            interview_type=InterviewType.TECHNICAL,
            difficulty=Difficulty.MEDIUM,
            history=history, asked=asked, last_signal=None,
        )
        assert q and q not in asked
        asked.add(q)
        history.append(QATurn(question=q, answer="some answer"))


@pytest.mark.asyncio
async def test_engine_summary_offline():
    engine = InterviewEngine(StubProvider())
    summary = await engine.summarize([QATurn("Q1", "A1")], avg_score=72)
    assert "72" in summary
