"""Integration tests for organizations + mentor dashboard + quota enforcement (Phase 10)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

API = "/api/v1"


async def _create_org(client: AsyncClient, headers: dict, slug: str = "acme") -> str:
    resp = await client.post(
        f"{API}/orgs", headers=headers, json={"name": "Acme Inc", "slug": slug})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_org_makes_caller_owner(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/orgs", headers=auth_headers, json={"name": "Acme Inc", "slug": "acme"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["your_role"] == "owner"
    assert body["member_count"] == 1
    assert body["plan"] == "team"


@pytest.mark.asyncio
async def test_add_member_and_list(client: AsyncClient, auth_headers, other_user_headers):
    # other_user_headers registers intruder@example.com (the member-to-be).
    org_id = await _create_org(client, auth_headers)
    add = await client.post(
        f"{API}/orgs/{org_id}/members", headers=auth_headers,
        json={"email": "intruder@example.com", "role": "member"})
    assert add.status_code == 201, add.text
    members = await client.get(f"{API}/orgs/{org_id}/members", headers=auth_headers)
    assert members.status_code == 200
    emails = {m["email"] for m in members.json()}
    assert {"candidate@example.com", "intruder@example.com"} <= emails


@pytest.mark.asyncio
async def test_non_member_cannot_view_org(client: AsyncClient, auth_headers, other_user_headers):
    org_id = await _create_org(client, auth_headers)
    # other_user is registered but not a member.
    resp = await client.get(f"{API}/orgs/{org_id}", headers=other_user_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_member_cannot_add_members_or_view_dashboard(
    client: AsyncClient, auth_headers, other_user_headers
):
    org_id = await _create_org(client, auth_headers)
    await client.post(
        f"{API}/orgs/{org_id}/members", headers=auth_headers,
        json={"email": "intruder@example.com", "role": "member"})
    # The plain member cannot add others...
    forbidden = await client.post(
        f"{API}/orgs/{org_id}/members", headers=other_user_headers,
        json={"email": "candidate@example.com", "role": "member"})
    assert forbidden.status_code in (403, 409)  # 403 (role) takes precedence
    assert forbidden.status_code == 403
    # ...nor view the mentor dashboard.
    dash = await client.get(f"{API}/orgs/{org_id}/dashboard", headers=other_user_headers)
    assert dash.status_code == 403


@pytest.mark.asyncio
async def test_mentor_dashboard_rollup(client: AsyncClient, auth_headers, other_user_headers):
    org_id = await _create_org(client, auth_headers)
    await client.post(
        f"{API}/orgs/{org_id}/members", headers=auth_headers,
        json={"email": "intruder@example.com", "role": "mentor"})
    resp = await client.get(f"{API}/orgs/{org_id}/dashboard", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["member_count"] == 2
    assert len(body["members"]) == 2
    assert {"user_id", "email", "role", "overall_readiness"} <= set(body["members"][0])


@pytest.mark.asyncio
async def test_list_my_orgs(client: AsyncClient, auth_headers):
    await _create_org(client, auth_headers, slug="acme")
    await _create_org(client, auth_headers, slug="globex")
    resp = await client.get(f"{API}/orgs", headers=auth_headers)
    assert resp.status_code == 200
    slugs = {o["slug"] for o in resp.json()}
    assert {"acme", "globex"} <= slugs
    assert all(o["your_role"] == "owner" for o in resp.json())


@pytest.mark.asyncio
async def test_org_requires_auth(client: AsyncClient):
    resp = await client.post(f"{API}/orgs", json={"name": "X", "slug": "x"})
    assert resp.status_code == 401


# ── Quota enforcement (tier limits) ─────────────────────────────────
@pytest.mark.asyncio
async def test_free_plan_agent_quota_enforced(client: AsyncClient):
    # A fresh user on the FREE plan (AGENT_WORKFLOW limit = 5).
    reg = await client.post(
        f"{API}/auth/register",
        json={"email": "quota-user@example.com", "password": "Sup3rSecret!"})
    headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
    body = {"resume_text": "Python FastAPI Kubernetes ML engineer with RAG experience."}

    for _ in range(5):
        ok = await client.post(f"{API}/agents/career-readiness", headers=headers, json=body)
        assert ok.status_code == 200, ok.text
    blocked = await client.post(f"{API}/agents/career-readiness", headers=headers, json=body)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "quota_exceeded"
