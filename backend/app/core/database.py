"""Async SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "")


def normalize_db_url(url: str) -> tuple[str, dict]:
    """Return (clean_url, connect_args).

    asyncpg does NOT understand libpq-style query params (``sslmode``,
    ``channel_binding``, ``ssl``) in the URL, so we strip them and pass SSL via
    ``connect_args`` instead. Managed Postgres (e.g. Neon/Supabase) requires SSL;
    local Postgres does not. SQLite is returned unchanged.
    """
    if url.startswith("sqlite"):
        return url, {}

    parts = urlsplit(url)
    sslmode = ssl_q = None
    kept: list[tuple[str, str]] = []
    # Tolerate malformed queries (e.g. a stray '??' producing a '?ssl' key).
    for raw_key, value in parse_qsl(parts.query, keep_blank_values=True):
        key = raw_key.lstrip("?").lower()
        if key == "sslmode":
            sslmode = value
        elif key == "ssl":
            ssl_q = value
        elif key == "channel_binding":
            continue
        else:
            kept.append((raw_key, value))
    clean = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )

    connect_args: dict = {}
    if "+asyncpg" in parts.scheme:
        host = (parts.hostname or "").lower()
        is_local = host in _LOCAL_HOSTS
        ssl_disabled = sslmode == "disable" or ssl_q in ("false", "disable")
        # Default to SSL for any non-local host (covers Neon/Supabase/RDS).
        if not is_local and not ssl_disabled:
            connect_args["ssl"] = True
    return clean, connect_args


def make_async_engine(url: str):
    clean, connect_args = normalize_db_url(url)
    kwargs: dict = {
        "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
        "pool_pre_ping": True,
        "future": True,
    }
    if not clean.startswith("sqlite"):
        kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE_SEC,
        )
    if connect_args:
        kwargs["connect_args"] = connect_args
    return create_async_engine(clean, **kwargs)


engine = make_async_engine(settings.DATABASE_URL)

# Read replica for read-heavy paths (analytics). Falls back to the primary engine.
_read_url = settings.READ_DATABASE_URL or settings.DATABASE_URL
read_engine = engine if _read_url == settings.DATABASE_URL else make_async_engine(_read_url)

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
