"""Structured logging configuration (structlog → JSON in prod, console in dev)."""
from __future__ import annotations

import logging

import structlog

from app.core.config import settings


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.is_production
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(message)s",
    )


logger = structlog.get_logger()
