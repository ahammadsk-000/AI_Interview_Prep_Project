"""Integration tests for the Analytics Dashboard (Phase 7).

Generates real activity through earlier-phase endpoints, then asserts the dashboard
aggregates it correctly.
"""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

API = "/api/v1"

STRONG = (
    "I would use a hash map for O(n) lookups. First I iterate the array, then I check the "
    "complement; for example with [2,7] and target 9 I return the indices. As a result the "
    "solution runs in linear time and I reduced cost from O(n^2)."
)
RESUME_TEXT = (
    "Jane Doe\njane@example.com | +1 415 555 0199 | linkedin.com/in/jane\n"
    "Experience\n- Led a RAG platform with Python, FastAPI, Kubernetes, reducing latency 40%.\n"
    "Skills\nPython, Docker, Kubernetes, PostgreSQL, FastAPI\nEducation\nB.Tech\n"
)
CHALLENGE = {
    "slug": "sum-two", "title": "Sum Two", "difficulty": "easy",
    "prompt": "Implement add(a, b).", "entrypoint": "add",
    "test_cases": [
        {"args": [1, 2], "expected": 3, "is_hidden": False},
        {"args": [4, 5], "expected": 9, "is_hidden": True},
    ],
}


async def _seed_activity(client: AsyncClient, auth_headers, mentor_headers):
    # Two graded answers (answer scores → dimensions/communication).
    for _ in range(2):
        await client.post(f"{API}/evaluation/answer", headers=auth_headers,
                          json={"question": "Two-sum?", "answer": STRONG})
    # Resume + two ATS analyses (ats_reports → ATS trend/improvement).
    up = await client.post(f"{API}/resumes", headers=auth_headers,
                           files={"file": ("r.txt", io.BytesIO(RESUME_TEXT.encode()), "text/plain")})
    rid = up.json()["id"]
    for jd in ("Need Python and Kubernetes.", "Need Python, Kubernetes, Terraform and Go."):
        await client.post(f"{API}/resumes/{rid}/analyze", headers=auth_headers,
                          json={"jd_text": jd})
    # A coding submission (accepted).
    created = await client.post(f"{API}/coding/challenges", headers=mentor_headers, json=CHALLENGE)
    cid = created.json()["id"]
    await client.post(f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
                      json={"language": "python", "source": "def add(a, b):\n    return a + b\n"})
    # An interview with an answer.
    start = await client.post(f"{API}/interviews/start", headers=auth_headers,
                              json={"type": "technical", "planned_questions": 2})
    sid = start.json()["session_id"]
    await client.post(f"{API}/interviews/sessions/{sid}/answer", headers=auth_headers,
                      json={"answer": STRONG})


@pytest.mark.asyncio
async def test_overview_aggregates_activity(client: AsyncClient, auth_headers, mentor_headers):
    await _seed_activity(client, auth_headers, mentor_headers)
    resp = await client.get(f"{API}/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["answers_graded"] == 2
    assert body["totals"]["coding_submissions"] == 1
    assert body["totals"]["interviews"] == 1
    assert body["coding"]["submissions"] == 1
    assert body["coding"]["accepted"] == 1
    assert body["coding"]["acceptance_rate"] == 1.0
    assert body["ats"]["reports"] == 2
    assert body["interviews"]["total"] == 1
    assert body["dimension_averages"]  # technical/communication/...
    assert body["overall_readiness"] is not None


@pytest.mark.asyncio
async def test_overview_empty_for_new_user(client: AsyncClient, auth_headers):
    resp = await client.get(f"{API}/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["answers_graded"] == 0
    assert body["coding"]["submissions"] == 0
    assert body["ats"]["reports"] == 0


@pytest.mark.asyncio
async def test_communication_trend(client: AsyncClient, auth_headers, mentor_headers):
    await _seed_activity(client, auth_headers, mentor_headers)
    resp = await client.get(
        f"{API}/analytics/trends?metric=communication&bucket=day", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["metric"] == "communication"
    assert body["summary"]["count"] >= 2
    assert body["points"]


@pytest.mark.asyncio
async def test_ats_trend_shows_reports(client: AsyncClient, auth_headers, mentor_headers):
    await _seed_activity(client, auth_headers, mentor_headers)
    resp = await client.get(f"{API}/analytics/trends?metric=ats", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["summary"]["count"] == 2


@pytest.mark.asyncio
async def test_snapshot_and_readiness_trend(client: AsyncClient, auth_headers, mentor_headers):
    await _seed_activity(client, auth_headers, mentor_headers)
    for _ in range(2):
        snap = await client.post(f"{API}/analytics/snapshots", headers=auth_headers,
                                 json={"metric": "readiness"})
        assert snap.status_code == 200
        assert snap.json()["value"] is not None
    trend = await client.get(f"{API}/analytics/trends?metric=readiness", headers=auth_headers)
    assert trend.status_code == 200
    assert trend.json()["summary"]["count"] == 2


@pytest.mark.asyncio
async def test_interview_history(client: AsyncClient, auth_headers, mentor_headers):
    await _seed_activity(client, auth_headers, mentor_headers)
    resp = await client.get(f"{API}/analytics/history?kind=interview", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["kind"] == "interview"
    assert "interview" in items[0]["label"]


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient):
    assert (await client.get(f"{API}/analytics/overview")).status_code == 401
