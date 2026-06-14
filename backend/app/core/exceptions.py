"""Application exception hierarchy + FastAPI handlers.

Domain/service code raises these provider-agnostic exceptions; the API layer
translates them to HTTP responses. Keeps business logic free of HTTP concerns.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__name__
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Error tracking: log with trace correlation, count it, never leak internals."""
        import structlog

        from app.core import metrics

        metrics.app_errors_total.inc(type=type(exc).__name__)
        structlog.get_logger().error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error",
                               "message": "An unexpected error occurred."}},
        )
