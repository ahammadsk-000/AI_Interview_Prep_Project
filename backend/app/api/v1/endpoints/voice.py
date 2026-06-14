"""Voice Interview endpoints: start session, ingest audio turn, fetch transcript."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile, status

from app.api.v1.deps import CurrentUser, VoiceSvc
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.schemas.interview import (
    StartVoiceRequest,
    TranscriptPublic,
    VoiceSessionPublic,
    VoiceTurnResponse,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/start", response_model=VoiceSessionPublic, status_code=status.HTTP_201_CREATED)
async def start_voice(
    payload: StartVoiceRequest, current: CurrentUser, voice: VoiceSvc
) -> VoiceSessionPublic:
    vs = await voice.start(current.id, payload.interview_session_id)
    return VoiceSessionPublic(
        id=vs.id,
        interview_session_id=vs.interview_session_id,
        status=vs.status.value,
        created_at=vs.created_at,
    )


@router.post("/{voice_session_id}/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    voice_session_id: uuid.UUID,
    current: CurrentUser,
    voice: VoiceSvc,
    audio: UploadFile = File(...),
) -> VoiceTurnResponse:
    content = await audio.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("Audio exceeds the upload size limit.")
    return await voice.ingest_turn(
        user_id=current.id,
        voice_session_id=voice_session_id,
        audio=content,
        mime=audio.content_type or "audio/wav",
    )


@router.get("/{voice_session_id}/transcript", response_model=list[TranscriptPublic])
async def get_transcript(
    voice_session_id: uuid.UUID, current: CurrentUser, voice: VoiceSvc
) -> list[TranscriptPublic]:
    records = await voice.transcripts(current.id, voice_session_id)
    return [TranscriptPublic.model_validate(t) for t in records]
