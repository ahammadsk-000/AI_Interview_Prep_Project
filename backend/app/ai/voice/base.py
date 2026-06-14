"""Speech ports (Dependency Inversion for the voice layer).

The voice pipeline depends on these Protocols, never on a concrete engine.
Real implementations (Whisper / Faster-Whisper / Deepgram for STT; ElevenLabs /
Piper for TTS) live behind the same interface and are selected by config. Tests
and offline mode use deterministic stubs — no audio backends, no network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Transcription:
    text: str
    confidence: float = 1.0


@runtime_checkable
class SpeechToText(Protocol):
    name: str

    async def transcribe(self, audio: bytes, *, mime: str = "audio/wav") -> Transcription:
        ...


@runtime_checkable
class TextToSpeech(Protocol):
    name: str

    async def synthesize(self, text: str, *, voice: str = "default") -> bytes:
        ...
