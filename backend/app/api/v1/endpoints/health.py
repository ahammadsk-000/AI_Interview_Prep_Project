"""Liveness & readiness probes."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.v1.deps import DbSession
from app.core.redis import redis_client

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — process is up."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: DbSession) -> dict[str, str]:
    """Readiness — dependencies reachable."""
    checks = {"database": "ok", "redis": "ok"}
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "down"
    try:
        await redis_client.ping()
    except Exception:
        checks["redis"] = "down"
    checks["status"] = "ok" if all(v == "ok" for k, v in checks.items() if k != "status") else "degraded"
    return checks
