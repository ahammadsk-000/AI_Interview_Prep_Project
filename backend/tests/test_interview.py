"""Integration tests for the AI Interviewer REST flow + WebSocket room (Phase 3)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.api.v1.deps import get_interview_service
from app.core.security import create_access_token
from app.domain.interview.enums import Difficulty, InterviewStatus, InterviewType
from app.main import create_app
from app.models.interview import Interview, InterviewSession
from app.services.interview_service import SessionState

API = "/api/v1"


async def _start(client: AsyncClient, headers: dict, planned: int = 3) -> dict:
    resp = await client.post(
        f"{API}/interviews/start",
        headers=headers,
        json={"type": "technical", "difficulty": "medium", "planned_questions": planned},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_start_interview_returns_first_question(client: AsyncClient, auth_headers):
    body = await _start(client, auth_headers)
    assert body["current_question"]
    assert body["questions_asked"] == 1
    assert body["done"] is False
    assert body["type"] == "technical"


@pytest.mark.asyncio
async def test_full_interview_flow_completes(client: AsyncClient, auth_headers):
    body = await _start(client, auth_headers, planned=3)
    session_id = body["session_id"]
    answers = [
        "I led the redesign of our payments service, reducing latency by 40%.",
        "I used Python, FastAPI, Redis and Kubernetes to scale throughput 3x.",
        "I measured impact with dashboards and cut incident rate significantly.",
    ]
    last = None
    for a in answers:
        resp = await client.post(
            f"{API}/interviews/sessions/{session_id}/answer",
            headers=auth_headers, json={"answer": a},
        )
        assert resp.status_code == 200, resp.text
        last = resp.json()
    assert last["done"] is True
    assert last["summary"]
    assert last["status"] == "completed"


@pytest.mark.asyncio
async def test_answering_completed_session_is_rejected(client: AsyncClient, auth_headers):
    body = await _start(client, auth_headers, planned=1)
    session_id = body["session_id"]
    done = await client.post(
        f"{API}/interviews/sessions/{session_id}/answer",
        headers=auth_headers, json={"answer": "A solid answer about my experience."},
    )
    assert done.json()["done"] is True
    again = await client.post(
        f"{API}/interviews/sessions/{session_id}/answer",
        headers=auth_headers, json={"answer": "another"},
    )
    assert again.status_code == 422


@pytest.mark.asyncio
async def test_turns_and_state_and_ownership(client: AsyncClient, auth_headers, other_user_headers):
    body = await _start(client, auth_headers)
    session_id = body["session_id"]
    await client.post(
        f"{API}/interviews/sessions/{session_id}/answer",
        headers=auth_headers, json={"answer": "My first answer."},
    )
    turns = await client.get(
        f"{API}/interviews/sessions/{session_id}/turns", headers=auth_headers
    )
    assert turns.status_code == 200
    roles = [t["role"] for t in turns.json()]
    assert roles[0] == "interviewer" and "candidate" in roles

    state = await client.get(
        f"{API}/interviews/sessions/{session_id}", headers=auth_headers
    )
    assert state.status_code == 200

    # Another user cannot see this session.
    intruder = await client.get(
        f"{API}/interviews/sessions/{session_id}", headers=other_user_headers
    )
    assert intruder.status_code == 404


@pytest.mark.asyncio
async def test_end_interview(client: AsyncClient, auth_headers):
    body = await _start(client, auth_headers)
    session_id = body["session_id"]
    resp = await client.post(
        f"{API}/interviews/sessions/{session_id}/end", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is True


# ── WebSocket room (transport-isolated with a fake service) ──────────
def _fake_state(question, done, summary=None, qa=1):
    interview = Interview(
        user_id=uuid.uuid4(), type=InterviewType.TECHNICAL, difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.COMPLETED if done else InterviewStatus.ACTIVE,
    )
    interview.id = uuid.uuid4()
    session = InterviewSession(
        interview_id=interview.id, round=1, current_difficulty=Difficulty.MEDIUM,
        planned_questions=3,
        status=InterviewStatus.COMPLETED if done else InterviewStatus.ACTIVE,
    )
    session.id = uuid.uuid4()
    return SessionState(
        interview=interview, session=session, questions_asked=qa,
        current_question=question, done=done, summary=summary,
        avg_score=70 if done else None,
    )


class _FakeInterviewService:
    def __init__(self) -> None:
        self.n = 0

    async def get_state(self, user_id, session_id):
        return _fake_state("Q1?", done=False, qa=1)

    async def submit_answer(self, user_id, session_id, answer):
        self.n += 1
        if self.n >= 2:
            return _fake_state(None, done=True, summary="Great session.", qa=3)
        return _fake_state(f"Q{self.n + 1}?", done=False, qa=self.n + 1)


def test_websocket_interview_room():
    app = create_app()
    app.dependency_overrides[get_interview_service] = lambda: _FakeInterviewService()
    token = create_access_token(str(uuid.uuid4()))
    session_id = uuid.uuid4()

    with TestClient(app) as tc:
        with tc.websocket_connect(f"/api/v1/interviews/ws/{session_id}?token={token}") as ws:
            first = ws.receive_json()
            assert first["event"] == "question"
            assert first["current_question"] == "Q1?"

            ws.send_json({"answer": "my first answer"})
            second = ws.receive_json()
            assert second["event"] == "question"
            assert second["current_question"] == "Q2?"

            ws.send_json({"answer": "my second answer"})
            final = ws.receive_json()
            assert final["event"] == "summary"
            assert final["done"] is True
    app.dependency_overrides.clear()


def test_websocket_rejects_bad_token():
    app = create_app()
    with TestClient(app) as tc:
        with pytest.raises(Exception):
            with tc.websocket_connect(f"/api/v1/interviews/ws/{uuid.uuid4()}?token=garbage") as ws:
                ws.receive_json()
