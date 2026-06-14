"""Subscription plans and their per-feature daily quotas.

Quotas are enforced server-side (see ``QuotaService``). ``-1`` means unlimited.
Tuning these is a product/pricing decision, isolated here from enforcement logic.
"""
from __future__ import annotations

from enum import Enum

from app.domain.identity.enums import SubscriptionPlan


class QuotaFeature(str, Enum):
    AI_INTERVIEW = "ai_interview"
    ANSWER_GRADING = "answer_grading"
    CODING_SUBMISSION = "coding_submission"
    AGENT_WORKFLOW = "agent_workflow"
    RESUME_ANALYSIS = "resume_analysis"


# plan -> feature -> daily limit (-1 = unlimited)
PLAN_LIMITS: dict[SubscriptionPlan, dict[QuotaFeature, int]] = {
    SubscriptionPlan.FREE: {
        QuotaFeature.AI_INTERVIEW: 3,
        QuotaFeature.ANSWER_GRADING: 20,
        QuotaFeature.CODING_SUBMISSION: 20,
        QuotaFeature.AGENT_WORKFLOW: 5,
        QuotaFeature.RESUME_ANALYSIS: 5,
    },
    SubscriptionPlan.PRO: {
        QuotaFeature.AI_INTERVIEW: 50,
        QuotaFeature.ANSWER_GRADING: 500,
        QuotaFeature.CODING_SUBMISSION: 500,
        QuotaFeature.AGENT_WORKFLOW: 100,
        QuotaFeature.RESUME_ANALYSIS: 100,
    },
    SubscriptionPlan.TEAM: dict.fromkeys(QuotaFeature, -1),
    SubscriptionPlan.ENTERPRISE: dict.fromkeys(QuotaFeature, -1),
}


def limit_for(plan: SubscriptionPlan, feature: QuotaFeature) -> int:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[SubscriptionPlan.FREE]).get(feature, 0)
