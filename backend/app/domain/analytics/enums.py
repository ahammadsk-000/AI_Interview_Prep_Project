"""Analytics enumerations."""
from __future__ import annotations

from enum import Enum


class MetricName(str, Enum):
    READINESS = "readiness"
    ATS = "ats"
    CODING = "coding"
    COMMUNICATION = "communication"
    TECHNICAL = "technical"


class Bucket(str, Enum):
    DAY = "day"
    WEEK = "week"


class HistoryKind(str, Enum):
    INTERVIEW = "interview"
    ANSWER = "answer"
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    ATS = "ats"
