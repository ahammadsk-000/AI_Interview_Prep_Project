"""Voice interview use-cases.

Overlays an interview session with speech: a candidate audio turn is transcribed
(STT), fed into the interview engine via :class:`InterviewService`, and the next
interviewer question is synthesized (TTS). Transcripts and recordings are persisted
for replay and speaker-attributed playback.

Real-time WebRTC streaming is a transport concern handled at the edge; this service
is the durable, testable core of the pipeline.
"""
from __future__ import annotations

import base64
import uuid

from app.ai.voice.base import SpeechToText, TextToSpeech
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.interview.enums import TurnRole, VoiceSessionStatus
from app.models.interview import VoiceSession
from app.repositories.interview import VoiceRepository
from app.schemas.interview import VoiceTurnResponse
from app.services.interview_service import InterviewService
from app.services.storage import FileStorage


class VoiceService:
    def __init__(
        self,
        voice_repo: VoiceRepository,
        interviews: InterviewService,
        stt: SpeechToText,
        tts: TextToSpeech,
        storage: FileStorage,
    ) -> None:
        self._repo = voice_repo
        self._interviews = interviews
        self._stt = stt
        self._tts = tts
        self._storage = storage

    async def start(self, user_id: uuid.UUID, interview_session_id: uuid.UUID) -> VoiceSession:
        # Ownership is enforced through the interview session.
        await self._interviews.get_owned_session(interview_session_id, user_id)
        return await self._repo.add_voice_session(
            VoiceSession(
                interview_session_id=interview_session_id,
                status=VoiceSessionStatus.ACTIVE,
                provider=f"{self._stt.name}/{self._tts.name}",
            )
        )

    async def _owned_voice_session(
        self, voice_session_id: uuid.UUID, user_id: uuid.UUID
    ) -> VoiceSession:
        vs = await self._repo.get_voice_session(voice_session_id)
        if vs is None:
            raise NotFoundError("Voice session not found.")
        # Re-check ownership via the linked interview session.
        await self._interviews.get_owned_session(vs.interview_session_id, user_id)
        return vs

    async def ingest_turn(
        self,
        *,
        user_id: uuid.UUID,
        voice_session_id: uuid.UUID,
        audio: bytes,
        mime: str = "audio/wav",
    ) -> VoiceTurnResponse:
        vs = await self._owned_voice_session(voice_session_id, user_id)
        if vs.status != VoiceSessionStatus.ACTIVE:
            raise ValidationError("Voice session has ended.")

        # 1) Speech-to-text (speaker: candidate).
        transcription = await self._stt.transcribe(audio, mime=mime)
        if not transcription.text or transcription.text == "[unintelligible audio]":
            raise ValidationError("Could not transcribe the audio. Please try again.")

        cand_key = self._storage.save(
            namespace=f"voice/{voice_session_id}", filename="candidate.bin", content=audio
        )
        idx = await self._repo.next_transcript_idx(voice_session_id)
        await self._repo.add_transcript(
            voice_session_id, speaker=TurnRole.CANDIDATE, text=transcription.text,
            order_idx=idx, confidence=transcription.confidence,
        )
        await self._repo.add_recording(
            voice_session_id, speaker=TurnRole.CANDIDATE, storage_key=cand_key
        )

        # 2) Drive the interview with the transcript.
        state = await self._interviews.submit_answer(
            user_id, vs.interview_session_id, transcription.text
        )

        if state.done:
            vs.status = VoiceSessionStatus.ENDED
            return VoiceTurnResponse(
                transcript=transcription.text,
                confidence=transcription.confidence,
                next_question=None, done=True, summary=state.summary,
            )

        # 3) Synthesize the next question (speaker: interviewer).
        question = state.current_question or ""
        audio_out = await self._tts.synthesize(question)
        q_key = self._storage.save(
            namespace=f"voice/{voice_session_id}", filename="interviewer.bin",
            content=audio_out,
        )
        await self._repo.add_transcript(
            voice_session_id, speaker=TurnRole.INTERVIEWER, text=question,
            order_idx=idx + 1, confidence=1.0,
        )
        await self._repo.add_recording(
            voice_session_id, speaker=TurnRole.INTERVIEWER, storage_key=q_key
        )
        return VoiceTurnResponse(
            transcript=transcription.text,
            confidence=transcription.confidence,
            next_question=question, done=False,
            question_audio_b64=base64.b64encode(audio_out).decode(),
        )

    async def transcripts(self, user_id: uuid.UUID, voice_session_id: uuid.UUID):
        await self._owned_voice_session(voice_session_id, user_id)
        return await self._repo.transcripts(voice_session_id)
