"""Alembic environment — async engine, metadata from app models."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.core.database import Base, engine, normalize_db_url

# Importing the model registry populates Base.metadata for autogenerate.
import app.models  # noqa: F401,E402

config = context.config
# NOTE: we do NOT push the DB URL into Alembic's ini config — ConfigParser does
# %-interpolation and would choke on URL-encoded characters. Online migrations use
# the app engine directly; offline mode builds the URL itself below.

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=normalize_db_url(settings.DATABASE_URL)[0],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # Reuse the app engine so SSL / connect_args handling is identical (asyncpg-safe).
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
