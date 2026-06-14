"""Integration tests for the Voice Interview System (Phase 3).

The Stub STT treats UTF-8 audio payloads as their transcript, so we can drive the
full pipeline (STT → interview engine → TTS) without real audio backends.
"""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

API = "/api/v1"


async def _start_interview(client: AsyncClient, headers: dict, planned: int = 3) -> str:
    resp = await client.post(
        f"{API}/interviews/start",
        headers=headers,
        json={"type": "technical", "planned_questions": planned},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


async def _start_voice(client: AsyncClient, headers: dict, interview_session_id: str) -> str:
    resp = await client.post(
        f"{API}/voice/start",
        headers=headers,
        json={"interview_session_id": interview_session_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _audio(text: str):
    return {"audio": ("turn.wav", io.BytesIO(text.encode("utf-8")), "audio/wav")}


@pytest.mark.asyncio
async def test_voice_turn_transcribes_and_advances(client: AsyncClient, auth_headers):
    isid = await _start_interview(client, auth_headers, planned=3)
    vsid = await _start_voice(client, auth_headers, isid)

    answer = "I built a RAG platform with Python and FastAPI, cutting latency by 40 percent."
    resp = await client.post(
        f"{API}/voice/{vsid}/turn", headers=auth_headers, files=_audio(answer)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transcript"] == answer
    assert body["confidence"] > 0
    assert body["done"] is False
    assert body["next_question"]
    assert body["question_audio_b64"]  # synthesized TTS payload


@pytest.mark.asyncio
async def test_voice_transcript_is_persisted(client: AsyncClient, auth_headers):
    isid = await _start_interview(client, auth_headers, planned=3)
    vsid = await _start_voice(client, auth_headers, isid)
    await client.post(
        f"{API}/voice/{vsid}/turn", headers=auth_headers,
        files=_audio("My answer about scaling Kubernetes services."),
    )
    tr = await client.get(f"{API}/voice/{vsid}/transcript", headers=auth_headers)
    assert tr.status_code == 200
    speakers = [t["speaker"] for t in tr.json()]
    assert "candidate" in speakers
    assert "interviewer" in speakers  # next question was transcribed too


@pytest.mark.asyncio
async def test_voice_start_rejects_other_users_session(
    client: AsyncClient, auth_headers, other_user_headers
):
    isid = await _start_interview(client, auth_headers, planned=3)
    resp = await client.post(
        f"{API}/voice/start", headers=other_user_headers,
        json={"interview_session_id": isid},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_voice_full_session_can_complete(client: AsyncClient, auth_headers):
    isid = await _start_interview(client, auth_headers, planned=2)
    vsid = await _start_voice(client, auth_headers, isid)
    body = None
    for a in ("First detailed answer about my project.",
              "Second detailed answer about the trade-offs I considered."):
        resp = await client.post(
            f"{API}/voice/{vsid}/turn", headers=auth_headers, files=_audio(a)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
    assert body["done"] is True
    assert body["summary"]
