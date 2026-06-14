"""Integration tests for the multi-agent workflow API (Phase 6)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

API = "/api/v1"

RESUME = (
    "Senior ML Engineer who led a RAG platform with Python, FastAPI and pgvector, "
    "reducing latency 40%. Skills: PyTorch, Docker, Kubernetes."
)
JD = "We need Python, Kubernetes, Terraform and Go for this ML platform role."
BEHAVIORAL = (
    "The situation was a failing service. My task was reliability. I led the fix: I analyzed "
    "the root cause then implemented caching. As a result errors dropped 60%."
)


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, auth_headers):
    resp = await client.get(f"{API}/agents", headers=auth_headers)
    assert resp.status_code == 200
    names = {a["name"] for a in resp.json()}
    assert {"resume_agent", "feedback_agent", "career_coach_agent"} <= names
    assert len(resp.json()) == 7


@pytest.mark.asyncio
async def test_career_readiness_full_run(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/agents/career-readiness", headers=auth_headers,
        json={"target_role": "GenAI Engineer", "resume_text": RESUME, "jd_text": JD,
              "behavioral_answer": BEHAVIORAL, "code": "def add(a,b):\n    return a+b\n"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["trace_id"]
    completed = [s for s in body["steps"] if s["status"] == "completed"]
    assert len(completed) == 7
    assert "feedback" in body["output"]
    assert "career_plan" in body["output"]
    assert 0 <= body["output"]["feedback"]["overall_readiness"] <= 100


@pytest.mark.asyncio
async def test_career_readiness_partial_inputs(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/agents/career-readiness", headers=auth_headers,
        json={"behavioral_answer": BEHAVIORAL},
    )
    assert resp.status_code == 200, resp.text
    steps = {s["agent"]: s["status"] for s in resp.json()["steps"]}
    assert steps["resume_agent"] == "skipped"
    assert steps["behavioral_evaluator_agent"] == "completed"


@pytest.mark.asyncio
async def test_career_readiness_requires_some_input(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/agents/career-readiness", headers=auth_headers, json={"language": "python"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_persisted_and_owner_only(client: AsyncClient, auth_headers, other_user_headers):
    created = await client.post(
        f"{API}/agents/career-readiness", headers=auth_headers,
        json={"target_role": "ML Engineer", "resume_text": RESUME},
    )
    run_id = created.json()["id"]

    listed = await client.get(f"{API}/agents/runs", headers=auth_headers)
    assert listed.status_code == 200
    assert any(r["id"] == run_id for r in listed.json())

    got = await client.get(f"{API}/agents/runs/{run_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["trace_id"]

    intruder = await client.get(f"{API}/agents/runs/{run_id}", headers=other_user_headers)
    assert intruder.status_code == 404


@pytest.mark.asyncio
async def test_requires_auth(client: AsyncClient):
    resp = await client.post(f"{API}/agents/career-readiness", json={"resume_text": RESUME})
    assert resp.status_code == 401
