"""Aggregate v1 API router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    analytics,
    auth,
    coding,
    evaluation,
    interview,
    organizations,
    resume,
    users,
    voice,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(resume.router)
api_router.include_router(interview.router)
api_router.include_router(voice.router)
api_router.include_router(coding.router)
api_router.include_router(evaluation.router)
api_router.include_router(agents.router)
api_router.include_router(analytics.router)
api_router.include_router(organizations.router)
