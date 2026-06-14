"""Integration tests: AI Answer Grading + Behavioral + session reports (Phase 5)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

API = "/api/v1"

STRONG_ANSWER = (
    "I would use a hash map for O(n) lookups. First I iterate the array, then for each "
    "element I check the complement; for example with [2,7] and target 9 I return the indices. "
    "As a result the solution runs in linear time, and I reduced the brute-force cost from O(n^2)."
)
STRONG_BEHAVIORAL = (
    "The situation was a failing checkout service. My task was to restore reliability. I led "
    "the effort: first I analyzed the root cause, then I implemented retries and Redis caching. "
    "As a result we reduced errors by 60% and I owned the rollout end to end."
)
WEAK = "Um, I guess I did some stuff and it kind of worked out, you know."


@pytest.mark.asyncio
async def test_grade_answer_returns_scores_and_prose(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/evaluation/answer", headers=auth_headers,
        json={"question": "Solve two-sum efficiently.", "answer": STRONG_ANSWER},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert 0 <= body["total"] <= 100
    assert body["score_out_of_10"] == round(body["total"] / 10, 1)
    assert set(body["dimensions"]) == {"technical", "communication", "completeness", "confidence"}
    assert body["suggested_better_answer"]
    assert body["industry_standard_answer"]
    assert body["score_id"]


@pytest.mark.asyncio
async def test_grade_answer_requires_auth(client: AsyncClient):
    resp = await client.post(f"{API}/evaluation/answer", json={"answer": "hi"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_grade_behavioral_star_and_recruiter(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/evaluation/behavioral", headers=auth_headers,
        json={"question": "Tell me about a hard problem.", "answer": STRONG_BEHAVIORAL},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert 0 <= body["behavioral_score"] <= 100
    assert "star_method" in body["competencies"]
    assert body["star_components"]["result"] is True
    assert body["recruiter_perspective"]


@pytest.mark.asyncio
async def test_weak_answer_scores_lower(client: AsyncClient, auth_headers):
    strong = await client.post(
        f"{API}/evaluation/answer", headers=auth_headers, json={"answer": STRONG_ANSWER})
    weak = await client.post(
        f"{API}/evaluation/answer", headers=auth_headers, json={"answer": WEAK})
    assert weak.json()["total"] < strong.json()["total"]


@pytest.mark.asyncio
async def test_list_and_get_score_ownership(client: AsyncClient, auth_headers, other_user_headers):
    graded = await client.post(
        f"{API}/evaluation/answer", headers=auth_headers, json={"answer": STRONG_ANSWER})
    score_id = graded.json()["score_id"]

    lst = await client.get(f"{API}/evaluation/scores", headers=auth_headers)
    assert lst.status_code == 200
    assert any(s["id"] == score_id for s in lst.json())

    mine = await client.get(f"{API}/evaluation/scores/{score_id}", headers=auth_headers)
    assert mine.status_code == 200
    intruder = await client.get(f"{API}/evaluation/scores/{score_id}", headers=other_user_headers)
    assert intruder.status_code == 404


# ── Session report (integration with the interview module) ──────────
async def _interview_with_answers(client: AsyncClient, headers: dict, n: int = 2) -> str:
    start = await client.post(
        f"{API}/interviews/start", headers=headers,
        json={"type": "technical", "planned_questions": n},
    )
    session_id = start.json()["session_id"]
    for _ in range(n):
        await client.post(
            f"{API}/interviews/sessions/{session_id}/answer", headers=headers,
            json={"answer": STRONG_ANSWER},
        )
    return session_id


@pytest.mark.asyncio
async def test_grade_session_produces_report(client: AsyncClient, auth_headers):
    session_id = await _interview_with_answers(client, auth_headers, n=2)
    resp = await client.post(
        f"{API}/evaluation/sessions/{session_id}/grade", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["graded_answers"] == 2
    assert 0 <= body["overall_score"] <= 100
    assert len(body["per_question"]) == 2
    assert body["summary"]
    assert body["report_id"]


@pytest.mark.asyncio
async def test_grade_session_ownership(client: AsyncClient, auth_headers, other_user_headers):
    session_id = await _interview_with_answers(client, auth_headers, n=2)
    resp = await client.post(
        f"{API}/evaluation/sessions/{session_id}/grade", headers=other_user_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_grade_session_without_answers_rejected(client: AsyncClient, auth_headers):
    start = await client.post(
        f"{API}/interviews/start", headers=auth_headers,
        json={"type": "hr", "planned_questions": 3},
    )
    session_id = start.json()["session_id"]
    resp = await client.post(
        f"{API}/evaluation/sessions/{session_id}/grade", headers=auth_headers
    )
    assert resp.status_code == 422
