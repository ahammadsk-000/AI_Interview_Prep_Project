"""Celery application (async offload: parsing, embeddings, grading, reports).

Run a worker:   celery -A app.worker.celery_app worker --loglevel=info
Run the beat:   celery -A app.worker.celery_app beat --loglevel=info

Tasks are intentionally thin wrappers that call the same service/domain logic used
by the API, so heavy work scales horizontally without duplicating business rules.
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "prepforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    task_track_started=True,
)

# Example scheduled job: capture readiness snapshots periodically (Phase 7 analytics).
celery_app.conf.beat_schedule = {
    "capture-readiness-daily": {
        "task": "app.worker.tasks.capture_daily_snapshots",
        "schedule": 24 * 60 * 60,  # seconds
    },
}
