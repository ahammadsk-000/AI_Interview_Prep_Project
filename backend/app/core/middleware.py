"""HTTP middleware: security headers + Redis sliding-window rate limiting."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.redis import redis_client


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window counter per client IP. Fails open if Redis is unavailable."""

    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self._limit = limit_per_minute or settings.RATE_LIMIT_PER_MINUTE

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client = request.client.host if request.client else "anonymous"
        key = f"ratelimit:{client}:{request.url.path}"
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, 60)
            if current > self._limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "rate_limited", "message": "Too many requests."}},
                )
        except Exception:
            pass  # fail open — availability over strict limiting
        return await call_next(request)
