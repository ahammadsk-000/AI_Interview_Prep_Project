"""Async SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {
        "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
        "pool_pre_ping": True,
        "future": True,
    }
    # SQLite (tests) doesn't take a sized connection pool; only tune real servers.
    if not url.startswith("sqlite"):
        kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE_SEC,
        )
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))

# Read replica for read-heavy paths (analytics). Falls back to the primary engine.
_read_url = settings.READ_DATABASE_URL or settings.DATABASE_URL
read_engine = (
    engine if _read_url == settings.DATABASE_URL
    else create_async_engine(_read_url, **_engine_kwargs(_read_url))
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

AsyncReadSessionLocal = async_sessionmaker(
    bind=read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base with common timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    """Reusable UUID primary-key column factory."""
    return mapped_column(primary_key=True, default=uuid.uuid4)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session (primary, read-write)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session bound to the read replica (or primary if none configured).

    Tests override this to the same in-memory engine as ``get_db``.
    """
    async with AsyncReadSessionLocal() as session:
        yield session
