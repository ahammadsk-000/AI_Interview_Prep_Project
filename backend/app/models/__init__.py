"""ORM model registry.

Importing this package imports every model so that ``Base.metadata`` is fully
populated for Alembic autogenerate and ``create_all`` in tests.
"""
from app.models.agent import AgentRun  # noqa: F401
from app.models.analytics import MetricSnapshot  # noqa: F401
from app.models.coding import (  # noqa: F401
    CodingChallenge,
    CodingSubmission,
    TestCase,
)
from app.models.evaluation import FeedbackReport, Score  # noqa: F401
from app.models.interview import (  # noqa: F401
    Interview,
    InterviewSession,
    Recording,
    Transcript,
    Turn,
    VoiceSession,
)
from app.models.organization import (  # noqa: F401
    Organization,
    OrganizationMembership,
)
from app.models.resume import (  # noqa: F401
    AtsReport,
    JobDescription,
    Resume,
    ResumeVersion,
)
from app.models.user import (  # noqa: F401
    AuditLog,
    OAuthAccount,
    Role,
    Session,
    Subscription,
    User,
    user_roles,
)

__all__ = [
    "User",
    "Role",
    "user_roles",
    "OAuthAccount",
    "Session",
    "Subscription",
    "AuditLog",
    "Resume",
    "ResumeVersion",
    "JobDescription",
    "AtsReport",
    "Interview",
    "InterviewSession",
    "Turn",
    "VoiceSession",
    "Transcript",
    "Recording",
    "CodingChallenge",
    "TestCase",
    "CodingSubmission",
    "Score",
    "FeedbackReport",
    "AgentRun",
    "MetricSnapshot",
    "Organization",
    "OrganizationMembership",
]
