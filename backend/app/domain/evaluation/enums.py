"""Evaluation bounded-context enumerations (grading + behavioral)."""
from __future__ import annotations

from enum import Enum


class SubjectType(str, Enum):
    ANSWER = "answer"
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    RESUME = "resume"


class GradingDimension(str, Enum):
    TECHNICAL = "technical"
    COMMUNICATION = "communication"
    COMPLETENESS = "completeness"
    CONFIDENCE = "confidence"


class StarComponent(str, Enum):
    SITUATION = "situation"
    TASK = "task"
    ACTION = "action"
    RESULT = "result"


class BehavioralCompetency(str, Enum):
    STAR = "star_method"
    COMMUNICATION = "communication"
    LEADERSHIP = "leadership"
    OWNERSHIP = "ownership"
    TEAMWORK = "teamwork"
    PROBLEM_SOLVING = "problem_solving"
