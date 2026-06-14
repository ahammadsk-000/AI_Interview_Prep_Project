"""Interview / Voice bounded-context enumerations."""
from __future__ import annotations

from enum import Enum


class InterviewType(str, Enum):
    HR = "hr"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    ML = "ml"
    GENAI = "genai"
    DEVOPS = "devops"
    PM = "pm"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    def harder(self) -> Difficulty:
        order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
        return order[min(order.index(self) + 1, len(order) - 1)]

    def easier(self) -> Difficulty:
        order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
        return order[max(order.index(self) - 1, 0)]


class InterviewStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TurnRole(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"


class VoiceSessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


# Default number of main questions per interview round.
DEFAULT_QUESTION_COUNT = 5
