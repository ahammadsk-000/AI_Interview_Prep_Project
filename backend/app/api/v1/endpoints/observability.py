"""Prometheus metrics exposition endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from app.core import metrics

router = APIRouter(tags=["system"])


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics.registry.render(), media_type=metrics.CONTENT_TYPE)
