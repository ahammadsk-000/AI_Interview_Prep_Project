"""AI Interviewer endpoints: REST flow + real-time WebSocket interview room."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.v1.deps import CurrentUser, InterviewSvc, user_id_from_token
from app.schemas.interview import (
    AnswerRequest,
    SessionStatePublic,
    StartInterviewRequest,
    TurnPublic,
)
from app.services.interview_service import SessionState

router = APIRouter(prefix="/interviews", tags=["interview"])


def _to_public(state: SessionState) -> SessionStatePublic:
    return SessionStatePublic(
        interview_id=state.interview.id,
        session_id=state.session.id,
        type=state.interview.type,
        status=state.session.status,
        current_difficulty=state.session.current_difficulty,
        planned_questions=state.session.planned_questions,
        questions_asked=state.questions_asked,
        current_question=state.current_question,
        done=state.done,
        summary=state.summary,
        avg_score=state.avg_score,
    )


def _ws_payload(state: SessionState, kind: str) -> dict:
    p = _to_public(state)
    # Envelope key is "event" to avoid colliding with the payload's interview "type".
    return {"event": kind, **p.model_dump(mode="json")}


@router.post("/start", response_model=SessionStatePublic)
async def start_interview(
    payload: StartInterviewRequest, current: CurrentUser, interviews: InterviewSvc
) -> SessionStatePublic:
    return _to_public(await interviews.start(current.id, payload))


@router.get("/sessions/{session_id}", response_model=SessionStatePublic)
async def get_session(
    session_id: uuid.UUID, current: CurrentUser, interviews: InterviewSvc
) -> SessionStatePublic:
    return _to_public(await interviews.get_state(current.id, session_id))


@router.post("/sessions/{session_id}/answer", response_model=SessionStatePublic)
async def answer(
    session_id: uuid.UUID, payload: AnswerRequest, current: CurrentUser, interviews: InterviewSvc
) -> SessionStatePublic:
    return _to_public(await interviews.submit_answer(current.id, session_id, payload.answer))


@router.post("/sessions/{session_id}/end", response_model=SessionStatePublic)
async def end_session(
    session_id: uuid.UUID, current: CurrentUser, interviews: InterviewSvc
) -> SessionStatePublic:
    return _to_public(await interviews.end(current.id, session_id))


@router.get("/sessions/{session_id}/turns", response_model=list[TurnPublic])
async def list_turns(
    session_id: uuid.UUID, current: CurrentUser, interviews: InterviewSvc
) -> list[TurnPublic]:
    # Ownership check, then return the ordered transcript of turns.
    await interviews.get_owned_session(session_id, current.id)
    turns = await interviews._repo.turns(session_id)
    return [TurnPublic.model_validate(t) for t in turns]


@router.websocket("/ws/{session_id}")
async def interview_room(
    websocket: WebSocket, session_id: uuid.UUID, interviews: InterviewSvc
) -> None:
    """Real-time interview room. Auth via `?token=<access_token>` query param.

    Protocol: server sends `{type: question, ...}`; client replies
    `{answer: "..."}`; repeats until `{type: summary, done: true}`.
    """
    user_id = user_id_from_token(websocket.query_params.get("token", ""))
    if user_id is None:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        state = await interviews.get_state(user_id, session_id)
        await websocket.send_json(_ws_payload(state, "summary" if state.done else "question"))
        while not state.done:
            data = await websocket.receive_json()
            answer = (data or {}).get("answer", "").strip()
            if not answer:
                await websocket.send_json({"event": "error", "message": "Answer is empty."})
                continue
            state = await interviews.submit_answer(user_id, session_id, answer)
            await websocket.send_json(
                _ws_payload(state, "summary" if state.done else "question")
            )
        await websocket.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:  # surface domain errors, then close
        await websocket.send_json({"event": "error", "message": str(exc)})
        await websocket.close(code=1011)
