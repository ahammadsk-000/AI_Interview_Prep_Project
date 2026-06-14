"""Celery tasks.

Kept minimal and observable. Real heavy-lift tasks (resume parsing, embedding
indexing, bulk grading, PDF report generation) plug in here and reuse the service
layer; they are scaffolded as the platform's async surface grows.
"""
from __future__ import annotations

import structlog

from app.worker.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.worker.tasks.ping")
def ping() -> str:
    """Liveness task used by deployment smoke checks."""
    return "pong"


@celery_app.task(name="app.worker.tasks.capture_daily_snapshots")
def capture_daily_snapshots() -> dict:
    """Scheduled hook to capture per-user readiness snapshots (Phase 7).

    Implementation iterates active users and calls AnalyticsService.capture_snapshot
    via a fresh async session; wired when the snapshot cadence is enabled in prod.
    """
    logger.info("capture_daily_snapshots_invoked")
    return {"status": "scheduled", "captured": 0}
