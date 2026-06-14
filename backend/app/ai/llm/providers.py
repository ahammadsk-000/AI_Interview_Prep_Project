"""Concrete LLM providers + a factory selected by settings.

- ``OllamaProvider``           : local default (``/api/chat``).
- ``OpenAICompatibleProvider`` : any OpenAI-compatible endpoint (incl. vLLM).
- ``StubProvider``             : deterministic, offline — used in tests and as a
                                 safe fallback when no backend is reachable.
"""
from __future__ import annotations

import httpx

from app.ai.llm.base import LLMProvider, Message
from app.core.config import settings


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self._base = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.LLM_MODEL

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self._base}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self) -> None:
        self._base = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._model = settings.LLM_MODEL
        self._key = settings.OPENAI_API_KEY

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class StubProvider:
    """Offline, deterministic provider. Echoes a structured, useful response so
    higher layers (and tests) work without any model backend."""

    name = "stub"

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return (
            "AI suggestions are unavailable offline; showing rule-based guidance. "
            f"(prompt chars: {len(user)})"
        )


def get_llm_provider() -> LLMProvider:
    if settings.ENVIRONMENT == "test":
        return StubProvider()
    match settings.LLM_PROVIDER:
        case "openai_compatible":
            return OpenAICompatibleProvider()
        case "vllm":
            return OpenAICompatibleProvider()  # vLLM exposes an OpenAI-compatible API
        case _:
            return OllamaProvider()
