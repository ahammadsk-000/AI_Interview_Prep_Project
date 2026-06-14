"""Reusable FastAPI dependencies: DB session, service wiring, auth & RBAC."""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, get_read_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.domain.identity.enums import RoleName
from app.models.user import User
from app.repositories.resume import (
    AtsReportRepository,
    JobDescriptionRepository,
    ResumeRepository,
)
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.resume_service import AtsService, JobService, ResumeService
from app.services.storage import get_storage

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadDbSession = Annotated[AsyncSession, Depends(get_read_db)]


# ── Service providers ───────────────────────────────────────────────
def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db), SessionRepository(db))


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


# ── Phase 2: Resume / Job / ATS service wiring ──────────────────────
def get_resume_service(db: DbSession) -> ResumeService:
    return ResumeService(ResumeRepository(db), get_storage())


def get_job_service(db: DbSession) -> JobService:
    return JobService(JobDescriptionRepository(db))


def get_ats_service(db: DbSession) -> AtsService:
    from app.ai.llm.providers import get_llm_provider

    resume_repo = ResumeRepository(db)
    return AtsService(
        ResumeService(resume_repo, get_storage()),
        JobService(JobDescriptionRepository(db)),
        AtsReportRepository(db),
        get_llm_provider(),
        resume_repo,
    )


ResumeSvc = Annotated[ResumeService, Depends(get_resume_service)]
JobSvc = Annotated[JobService, Depends(get_job_service)]
AtsSvc = Annotated[AtsService, Depends(get_ats_service)]


# ── Phase 3: Interview / Voice service wiring ───────────────────────
def get_interview_service(db: DbSession) -> InterviewService:  # noqa: F821
    from app.ai.interview_engine import InterviewEngine
    from app.ai.llm.providers import get_llm_provider
    from app.repositories.interview import InterviewRepository
    from app.services.interview_service import InterviewService

    return InterviewService(
        InterviewRepository(db),
        InterviewEngine(get_llm_provider()),
        ResumeRepository(db),
    )


def get_voice_service(db: DbSession) -> VoiceService:  # noqa: F821
    from app.ai.voice.providers import get_stt, get_tts
    from app.repositories.interview import VoiceRepository
    from app.services.storage import get_storage
    from app.services.voice_service import VoiceService

    return VoiceService(
        VoiceRepository(db),
        get_interview_service(db),
        get_stt(),
        get_tts(),
        get_storage(),
    )


from app.services.interview_service import InterviewService  # noqa: E402
from app.services.voice_service import VoiceService  # noqa: E402

InterviewSvc = Annotated[InterviewService, Depends(get_interview_service)]
VoiceSvc = Annotated[VoiceService, Depends(get_voice_service)]


# ── Phase 4: Coding / DSA service wiring ────────────────────────────
def get_challenge_service(db: DbSession) -> ChallengeService:  # noqa: F821
    from app.repositories.coding import ChallengeRepository
    from app.services.coding_service import ChallengeService

    return ChallengeService(ChallengeRepository(db))


def get_submission_service(db: DbSession) -> SubmissionService:  # noqa: F821
    from app.ai.execution.factory import get_execution_engine
    from app.repositories.coding import ChallengeRepository, SubmissionRepository
    from app.services.coding_service import ChallengeService, SubmissionService

    return SubmissionService(
        ChallengeService(ChallengeRepository(db)),
        SubmissionRepository(db),
        get_execution_engine(),
    )


from app.services.coding_service import (  # noqa: E402
    ChallengeService,
    SubmissionService,
)

ChallengeSvc = Annotated[ChallengeService, Depends(get_challenge_service)]
SubmissionSvc = Annotated[SubmissionService, Depends(get_submission_service)]


# ── Phase 5: Evaluation / Grading service wiring ────────────────────
def get_grading_service(db: DbSession) -> GradingService:  # noqa: F821
    from app.ai.llm.providers import get_llm_provider
    from app.repositories.evaluation import FeedbackReportRepository, ScoreRepository
    from app.services.evaluation_service import GradingService

    return GradingService(
        ScoreRepository(db),
        FeedbackReportRepository(db),
        get_llm_provider(),
        get_interview_service(db),
    )


from app.services.evaluation_service import GradingService  # noqa: E402

GradingSvc = Annotated[GradingService, Depends(get_grading_service)]


# ── Phase 6: Multi-agent workflow wiring ────────────────────────────
def get_agent_service(db: DbSession) -> AgentWorkflowService:  # noqa: F821
    from app.ai.llm.providers import get_llm_provider
    from app.repositories.agent import AgentRunRepository
    from app.services.agent_service import AgentWorkflowService

    return AgentWorkflowService(AgentRunRepository(db), get_llm_provider())


from app.services.agent_service import AgentWorkflowService  # noqa: E402

AgentSvc = Annotated[AgentWorkflowService, Depends(get_agent_service)]


# ── Phase 7/10: Analytics wiring (cache + read-your-writes on the primary) ──
# The dashboard endpoints both read and write (snapshot capture), so they use a
# single primary session for read-your-writes consistency. Pure-read consumers
# (e.g. the org mentor dashboard) route their analytics through the read replica.
def get_analytics_service(db: DbSession) -> AnalyticsService:  # noqa: F821
    from app.core.cache import get_cache
    from app.repositories.analytics import AnalyticsRepository

    return AnalyticsService(AnalyticsRepository(db), get_cache())


from app.services.analytics_service import AnalyticsService  # noqa: E402

AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]


# ── Phase 10: Organizations (multi-tenancy) wiring ──────────────────
def get_org_service(db: DbSession, read_db: ReadDbSession) -> OrganizationService:  # noqa: F821
    from app.core.cache import get_cache
    from app.repositories.analytics import AnalyticsRepository
    from app.repositories.organization import OrgRepository
    from app.services.analytics_service import AnalyticsService as _AnalyticsService
    from app.services.organization_service import OrganizationService

    analytics = _AnalyticsService(AnalyticsRepository(read_db), get_cache())
    return OrganizationService(OrgRepository(db), UserRepository(db), analytics)


from app.services.organization_service import OrganizationService  # noqa: E402

OrgSvc = Annotated[OrganizationService, Depends(get_org_service)]


# ── Phase 10: Subscription-tier quotas ──────────────────────────────
from app.services.quota_service import InMemoryCounterStore, QuotaService  # noqa: E402

# Process-local store (single replica / tests). Redis is used in production.
_quota_store = InMemoryCounterStore()


def get_quota_service() -> QuotaService:
    from datetime import UTC, datetime

    day = datetime.now(UTC).date().isoformat()
    if settings.ENVIRONMENT == "test":
        return QuotaService(_quota_store, day=day)
    from app.core.redis import redis_client
    from app.services.quota_service import RedisCounterStore

    return QuotaService(RedisCounterStore(redis_client), day=day)


def require_quota(feature):
    """Dependency factory enforcing the caller's daily plan quota for a feature."""
    from app.domain.identity.enums import SubscriptionPlan

    async def _checker(
        user: CurrentUser,
        quota: Annotated[QuotaService, Depends(get_quota_service)],
    ) -> User:
        plan = user.subscription.plan if user.subscription else SubscriptionPlan.FREE
        await quota.enforce(user.id, plan, feature)
        return user

    return _checker


def user_id_from_token(token: str) -> uuid.UUID | None:
    """Decode a bearer access token to its subject (used for WebSocket auth).

    Returns the user id without a DB hit; ownership is still enforced in services.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return _as_uuid(payload.get("sub", ""))


# ── Authentication ──────────────────────────────────────────────────
async def get_current_user(
    request: Request,
    users: UserRepo,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing bearer token.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type.")

    sub = payload.get("sub")
    user = await users.get(_as_uuid(sub)) if sub else None
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive.")
    request.state.user_id = str(user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleName):
    """Dependency factory enforcing that the caller holds at least one role."""
    allowed: Iterable[RoleName] = roles

    async def _checker(user: CurrentUser) -> User:
        if not any(user.has_role(r) for r in allowed):
            raise PermissionDeniedError("Insufficient role for this action.")
        return user

    return _checker


def _as_uuid(value: str):
    import uuid

    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        return None
