"""Unit tests for the DSA evaluation internals (complexity, quality, evaluator)."""
from __future__ import annotations

from app.ai.execution.base import CaseResult, ExecutionResult
from app.domain.coding.complexity import estimate
from app.domain.coding.enums import (
    ChallengeDifficulty,
    ComplexityClass,
    Language,
    SubmissionStatus,
)
from app.domain.coding.evaluator import evaluate
from app.domain.coding.quality import assess

PY = Language.PYTHON


def test_complexity_constant():
    assert estimate("def f(x):\n    return x + 1\n", PY).time == ComplexityClass.O_1


def test_complexity_single_loop():
    src = "def f(a):\n    s = 0\n    for x in a:\n        s += x\n    return s\n"
    assert estimate(src, PY).time == ComplexityClass.O_N


def test_complexity_nested_loops():
    src = (
        "def f(a):\n    c = 0\n    for i in a:\n        for j in a:\n"
        "            c += 1\n    return c\n"
    )
    assert estimate(src, PY).time == ComplexityClass.O_N2


def test_complexity_sorting():
    src = "def f(a):\n    return sorted(a)\n"
    assert estimate(src, PY).time == ComplexityClass.O_N_LOG_N


def test_complexity_exponential_recursion():
    src = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n-1) + fib(n-2)\n"
    assert estimate(src, PY).time == ComplexityClass.O_2N


def test_quality_penalizes_bare_except():
    src = (
        "def f(x):\n"
        + "    y = 0\n" * 14
        + "    try:\n        return x\n    except:\n        return None\n"
    )
    report = assess(src, PY)
    assert report.score < 100
    assert any("except" in n.lower() for n in report.notes)


def test_evaluate_combines_signals():
    src = "def add(a, b):\n    return a + b\n"
    execution = ExecutionResult(
        status=SubmissionStatus.ACCEPTED, passed=3, total=3,
        cases=[
            CaseResult(0, True, False, 0.1),
            CaseResult(1, True, True, 0.1),
            CaseResult(2, True, True, 0.1),
        ],
        runtime_ms=0.3,
    )
    ev = evaluate(
        source=src, language=PY, entrypoint="add",
        difficulty=ChallengeDifficulty.EASY, execution=execution,
    )
    assert ev.correctness_score == 100
    assert ev.edge_case_score == 100  # both hidden cases passed
    assert ev.readiness_score >= 90
    assert ev.time_complexity == "O(1)"
