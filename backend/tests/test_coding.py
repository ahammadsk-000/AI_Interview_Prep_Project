"""Integration tests: Coding Platform + DSA Evaluation (Phase 4).

These execute real Python via the LocalPythonExecutionEngine (the submitted code
is our own benign test code), exercising the full run→execute→evaluate pipeline.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

API = "/api/v1"

CHALLENGE = {
    "slug": "add-two-numbers",
    "title": "Add Two Numbers",
    "difficulty": "easy",
    "prompt": "Implement add(a, b) returning the sum of two integers.",
    "entrypoint": "add",
    "starter_code": {"python": "def add(a, b):\n    pass\n"},
    "tags": ["math", "warmup"],
    "test_cases": [
        {"args": [1, 2], "expected": 3, "is_hidden": False},
        {"args": [5, 5], "expected": 10, "is_hidden": False},
        {"args": [-1, 1], "expected": 0, "is_hidden": True},
        {"args": [100, 200], "expected": 300, "is_hidden": True},
    ],
}

GOOD = "def add(a, b):\n    return a + b\n"
WRONG = "def add(a, b):\n    return a - b\n"
BROKEN = "def add(a, b)\n    return a + b\n"  # syntax error


async def _create_challenge(client: AsyncClient, mentor_headers: dict) -> str:
    resp = await client.post(f"{API}/coding/challenges", headers=mentor_headers, json=CHALLENGE)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_challenge_hides_hidden_cases(client: AsyncClient, mentor_headers):
    resp = await client.post(f"{API}/coding/challenges", headers=mentor_headers, json=CHALLENGE)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["visible_test_cases"]) == 2
    assert body["hidden_test_count"] == 2


@pytest.mark.asyncio
async def test_regular_user_cannot_create_challenge(client: AsyncClient, auth_headers):
    resp = await client.post(f"{API}/coding/challenges", headers=auth_headers, json=CHALLENGE)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_challenge_does_not_leak_hidden(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.get(f"{API}/coding/challenges/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["hidden_test_count"] == 2
    assert len(resp.json()["visible_test_cases"]) == 2


@pytest.mark.asyncio
async def test_run_correct_solution_passes_visible(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.post(
        f"{API}/coding/challenges/{cid}/run", headers=auth_headers,
        json={"language": "python", "source": GOOD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["passed"] == body["total"] == 2  # visible only
    assert body["correctness_score"] == 100


@pytest.mark.asyncio
async def test_submit_correct_solution_runs_hidden(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.post(
        f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
        json={"language": "python", "source": GOOD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["passed"] == body["total"] == 4
    assert body["edge_case_score"] == 100
    assert body["readiness_score"] >= 85
    assert body["submission_id"]
    # Hidden case details are not leaked.
    hidden = [c for c in body["cases"] if c["is_hidden"]]
    assert hidden and all(c["runtime_ms"] is None for c in hidden)


@pytest.mark.asyncio
async def test_submit_wrong_solution_reports_failures(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.post(
        f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
        json={"language": "python", "source": WRONG},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "wrong_answer"
    assert body["passed"] < body["total"]
    assert any("failed" in s.lower() for s in body["suggestions"])


@pytest.mark.asyncio
async def test_submit_syntax_error_is_compile_error(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.post(
        f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
        json={"language": "python", "source": BROKEN},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "compile_error"


@pytest.mark.asyncio
async def test_unsupported_language_local_engine(client: AsyncClient, mentor_headers, auth_headers):
    cid = await _create_challenge(client, mentor_headers)
    resp = await client.post(
        f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
        json={"language": "java", "source": "class S { static int add(int a,int b){return a+b;} }"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "unsupported"


@pytest.mark.asyncio
async def test_get_submission_owner_only(client: AsyncClient, mentor_headers, auth_headers, other_user_headers):
    cid = await _create_challenge(client, mentor_headers)
    sub = await client.post(
        f"{API}/coding/challenges/{cid}/submit", headers=auth_headers,
        json={"language": "python", "source": GOOD},
    )
    sid = sub.json()["submission_id"]
    mine = await client.get(f"{API}/coding/submissions/{sid}", headers=auth_headers)
    assert mine.status_code == 200
    assert mine.json()["readiness_score"] >= 85
    intruder = await client.get(f"{API}/coding/submissions/{sid}", headers=other_user_headers)
    assert intruder.status_code == 404
