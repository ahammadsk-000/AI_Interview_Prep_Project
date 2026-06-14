"""Identity bounded-context enumerations (framework-free domain values)."""
from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    ADMIN = "ADMIN"
    MENTOR = "MENTOR"
    RECRUITER = "RECRUITER"
    USER = "USER"


class ExperienceLevel(str, Enum):
    FRESHER = "fresher"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"


class SubscriptionPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"


# Default role assigned at registration.
DEFAULT_ROLE = RoleName.USER

# Roles seeded into the database on first migration/bootstrap.
ALL_ROLES = tuple(RoleName)
