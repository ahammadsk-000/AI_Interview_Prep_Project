"""Organization (multi-tenancy) enumerations."""
from __future__ import annotations

from enum import Enum


class OrgRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MENTOR = "mentor"
    MEMBER = "member"


# Roles permitted to view the org mentor dashboard and manage members.
MANAGER_ROLES = (OrgRole.OWNER, OrgRole.ADMIN, OrgRole.MENTOR)
ADMIN_ROLES = (OrgRole.OWNER, OrgRole.ADMIN)
