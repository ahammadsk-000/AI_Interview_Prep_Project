"""Authentication & RBAC integration tests (Module 1)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

API = "/api/v1"


@pytest.mark.asyncio
async def test_register_returns_user_and_tokens(client: AsyncClient):
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": "new@example.com", "password": "Sup3rSecret!", "full_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "new@example.com"
    assert "USER" in body["user"]["roles"]
    assert body["user"]["plan"] == "free"
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    # Never leak the password hash.
    assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_conflicts(client: AsyncClient, registered_user):
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": "candidate@example.com", "password": "AnotherP@ss1"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


@pytest.mark.asyncio
async def test_register_rejects_short_password(client: AsyncClient):
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, registered_user):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "candidate@example.com", "password": "Sup3rSecret!"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client: AsyncClient, registered_user):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "candidate@example.com", "password": "WrongPassword1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_error"


@pytest.mark.asyncio
async def test_login_unknown_email_rejected(client: AsyncClient):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "ghost@example.com", "password": "Whatever123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_authentication(client: AsyncClient):
    resp = await client.get(f"{API}/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient, registered_user):
    token = registered_user["tokens"]["access_token"]
    resp = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "candidate@example.com"
    assert resp.json()["target_role"] == "GenAI Engineer"


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, registered_user):
    token = registered_user["tokens"]["access_token"]
    resp = await client.patch(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Ada Lovelace", "experience_level": "senior"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Ada Lovelace"
    assert resp.json()["experience_level"] == "senior"


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient, registered_user):
    old_refresh = registered_user["tokens"]["refresh_token"]
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    assert new_tokens["access_token"]
    # Old refresh token is now revoked (rotation) — reuse must fail.
    reuse = await client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient, registered_user):
    refresh = registered_user["tokens"]["refresh_token"]
    out = await client.post(f"{API}/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 200
    after = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_admin_only_user_list_forbidden_for_regular_user(client: AsyncClient, registered_user):
    token = registered_user["tokens"]["access_token"]
    resp = await client.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
