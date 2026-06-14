"""Multi-agent bounded-context enumerations + small mappings."""
from __future__ import annotations

from enum import Enum

from app.domain.interview.enums import InterviewType


class AgentName(str, Enum):
    RESUME = "resume_agent"
    ATS = "ats_agent"
    INTERVIEWER = "interviewer_agent"
    CODING_EVALUATOR = "coding_evaluator_agent"
    BEHAVIORAL = "behavioral_evaluator_agent"
    FEEDBACK = "feedback_agent"
    CAREER_COACH = "career_coach_agent"


class StepStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def role_to_interview_type(role: str | None) -> InterviewType:
    """Map a target role string onto the closest interview type."""
    r = (role or "").lower()
    if "genai" in r or "llm" in r or "generative" in r:
        return InterviewType.GENAI
    if "ml" in r or "machine learning" in r or "data scien" in r or "ai engineer" in r:
        return InterviewType.ML
    if "devops" in r or "sre" in r or "platform" in r or "infra" in r:
        return InterviewType.DEVOPS
    if "product" in r or r.strip() == "pm" or "program manager" in r:
        return InterviewType.PM
    if "system" in r or "architect" in r:
        return InterviewType.SYSTEM_DESIGN
    if "hr" in r or "recruit" in r:
        return InterviewType.HR
    return InterviewType.TECHNICAL
