"""Speech provider implementations + factories.

- ``StubSpeechToText`` / ``StubTextToSpeech``: deterministic, offline. The STT
  stub treats UTF-8 audio payloads as their own transcript (a clean test seam);
  real audio yields a placeholder. The TTS stub returns a deterministic byte blob.
- Real providers (Faster-Whisper, ElevenLabs, …) are wired in a later phase behind
  the same Protocols; selection is by config so call sites never change.
"""
from __future__ import annotations

from app.ai.voice.base import SpeechToText, TextToSpeech, Transcription
from app.core.config import settings


class StubSpeechToText:
    name = "stub"

    async def transcribe(self, audio: bytes, *, mime: str = "audio/wav") -> Transcription:
        try:
            text = audio.decode("utf-8")
            # Heuristic: if it decodes to readable text, treat it as the transcript.
            if text.isprintable() or "\n" in text:
                return Transcription(text=text.strip(), confidence=0.99)
        except UnicodeDecodeError:
            pass
        return Transcription(text="[unintelligible audio]", confidence=0.0)


class StubTextToSpeech:
    name = "stub"

    async def synthesize(self, text: str, *, voice: str = "default") -> bytes:
        return b"PREPFORGE_TTS_STUB::" + text.encode("utf-8")


def get_stt() -> SpeechToText:
    # Real STT (faster-whisper/deepgram) is selected here in a later phase.
    if settings.ENVIRONMENT == "test":
        return StubSpeechToText()
    return StubSpeechToText()


def get_tts() -> TextToSpeech:
    if settings.ENVIRONMENT == "test":
        return StubTextToSpeech()
    return StubTextToSpeech()
