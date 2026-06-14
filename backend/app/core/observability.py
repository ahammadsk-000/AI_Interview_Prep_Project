"""Request tracing, HTTP metrics, and structured-log correlation.

The middleware assigns/propagates a W3C trace id + request id, binds them to the
structlog context (so every log line within a request is correlated — Loki-ready),
records Prometheus HTTP metrics, and adds trace headers to the response.

OpenTelemetry export is optional and loaded lazily (``OTEL_ENABLED``); when off,
the in-house metrics + trace ids still provide full request observability.
"""
from __future__ import annotations

import secrets
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import metrics
from app.core.config import settings

logger = structlog.get_logger()


def _parse_traceparent(header: str | None) -> str | None:
    # 00-<32 hex trace-id>-<16 hex span-id>-<2 hex flags>
    if not header:
        return None
    parts = header.split("-")
    if len(parts) == 4 and len(parts[1]) == 32:
        return parts[1]
    return None


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = _parse_traceparent(request.headers.get("traceparent")) or uuid.uuid4().hex
        span_id = secrets.token_hex(8)
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id, request_id=request_id,
            method=request.method, path=request.url.path,
        )
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        metrics.http_requests_in_progress.inc(method=request.method)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            response.headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
            return response
        finally:
            duration = time.perf_counter() - start
            template = _route_template(request)
            metrics.http_requests_in_progress.dec(method=request.method)
            if settings.METRICS_ENABLED and not template.endswith("/metrics"):
                metrics.http_request_duration_seconds.observe(
                    duration, method=request.method, path=template)
                metrics.http_requests_total.inc(
                    method=request.method, path=template, status=str(status_code))
            logger.info("request", status=status_code, duration_ms=round(duration * 1000, 2))


def setup_opentelemetry(app) -> None:
    """Optionally instrument with OpenTelemetry (lazy import; no-op if disabled)."""
    if not settings.OTEL_ENABLED:
        return
    try:  # pragma: no cover - exercised only when the OTel stack is installed
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel_enabled", service=settings.OTEL_SERVICE_NAME)
    except Exception as exc:  # pragma: no cover
        logger.warning("otel_setup_failed", error=str(exc))
