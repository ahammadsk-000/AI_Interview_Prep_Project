"""Coding / DSA bounded-context enumerations."""
from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    GO = "go"
    CPP = "cpp"
    CSHARP = "csharp"


class ChallengeDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"          # all test cases passed
    WRONG_ANSWER = "wrong_answer"  # some cases failed
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    TIME_LIMIT = "time_limit"
    UNSUPPORTED = "unsupported"     # language not runnable by the active engine


class ComplexityClass(str, Enum):
    O_1 = "O(1)"
    O_LOG_N = "O(log n)"
    O_N = "O(n)"
    O_N_LOG_N = "O(n log n)"
    O_N2 = "O(n^2)"
    O_N3 = "O(n^3)"
    O_2N = "O(2^n)"
    UNKNOWN = "O(?)"

    @property
    def rank(self) -> int:
        order = [
            ComplexityClass.O_1, ComplexityClass.O_LOG_N, ComplexityClass.O_N,
            ComplexityClass.O_N_LOG_N, ComplexityClass.O_N2, ComplexityClass.O_N3,
            ComplexityClass.O_2N, ComplexityClass.UNKNOWN,
        ]
        return order.index(self)
