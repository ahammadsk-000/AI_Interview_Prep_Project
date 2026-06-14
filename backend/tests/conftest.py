"""Test fixtures: in-memory async SQLite DB + ASGI client with overrides."""
from __future__ import annotations

import os
import tempfile

# Must be set before any `app.*` import so cached Settings pick it up
# (cheap Argon2, isolated on-disk storage for uploads).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="prepforge_test_storage_"))

import asyncio  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db, get_read_db
from app.domain.identity.enums import ALL_ROLES
from app.main import create_app
from app.models.user import Role


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    # Seed RBAC roles once.
    async with factory() as s:
        for role_name in ALL_ROLES:
            s.add(Role(name=role_name, description=f"{role_name.value} role"))
        await s.commit()
    return factory


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_read_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_read_db] = _override_get_read_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def error_client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """Like ``client`` but returns the app's 500 response (as uvicorn would) instead
    of re-raising — used to test the unhandled-exception handler."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Registers a baseline user and returns the AuthResponse payload."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "Sup3rSecret!",
            "full_name": "Ada Candidate",
            "target_role": "GenAI Engineer",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def auth_headers(registered_user: dict) -> dict:
    return {"Authorization": f"Bearer {registered_user['tokens']['access_token']}"}


@pytest_asyncio.fixture
async def other_user_headers(client: AsyncClient) -> dict:
    """A second, distinct user — for cross-user ownership checks."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "intruder@example.com", "password": "An0therPass!"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['tokens']['access_token']}"}


@pytest_asyncio.fixture
async def mentor_headers(client: AsyncClient, session_factory) -> dict:
    """A user elevated to the MENTOR role (e.g. for authoring coding challenges)."""
    import uuid as _uuid

    from sqlalchemy import select

    from app.domain.identity.enums import RoleName
    from app.models.user import Role, User

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "mentor@example.com", "password": "MentorP@ss1"},
    )
    assert resp.status_code == 201, resp.text
    user_id = _uuid.UUID(resp.json()["user"]["id"])
    async with session_factory() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one()
        role = (await s.execute(select(Role).where(Role.name == RoleName.MENTOR))).scalar_one()
        user.roles.append(role)
        await s.commit()
    return {"Authorization": f"Bearer {resp.json()['tokens']['access_token']}"}
