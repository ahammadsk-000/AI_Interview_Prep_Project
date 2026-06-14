"""LLM provider port (Dependency Inversion for the AI layer).

All AI features depend on this Protocol, never on a concrete vendor. Swapping
Ollama ↔ vLLM ↔ OpenAI-compatible is a config change (``LLM_PROVIDER``), and tests
use a deterministic stub — no network, no model weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        """Return a single completion for the given conversation."""
        ...
