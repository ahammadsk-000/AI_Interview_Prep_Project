"""Composition root — wires settings, middleware, routers, and lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import health, observability
from app.api.v1.router import api_router
from app.bootstrap import seed_challenges, seed_roles
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.observability import ObservabilityMiddleware, setup_opentelemetry


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("startup", app=settings.APP_NAME, env=settings.ENVIRONMENT)
    if settings.ENVIRONMENT != "test":  # tests seed via their own fixtures
        try:
            await seed_roles()
            await seed_challenges()
        except Exception as exc:  # don't crash boot if DB not migrated yet in dev
            logger.warning("seed_skipped", error=str(exc))
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="AI Interview Preparation Platform API",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )

    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(SecurityHeadersMiddleware)
    # Rate limiting depends on Redis; disabled under tests and when no Redis is run.
    if settings.ENVIRONMENT != "test" and settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
    # Added last → outermost: sees every request first and every response last.
    app.add_middleware(ObservabilityMiddleware)

    register_exception_handlers(app)
    setup_opentelemetry(app)

    # Health + metrics at root; versioned business API under the prefix.
    app.include_router(health.router)
    app.include_router(observability.router)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Test-only route to exercise the unhandled-exception handler + error metric.
    if settings.ENVIRONMENT == "test":
        @app.get("/_debug/boom", include_in_schema=False)
        async def _boom() -> None:
            raise RuntimeError("intentional test failure")

    return app


app = create_app()
