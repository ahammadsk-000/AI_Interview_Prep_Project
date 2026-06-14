"""LLM-written qualitative grading prose, behind the LLMProvider port.

Each helper degrades to a concise deterministic template when the provider is the
offline stub or the call fails — so grading always returns useful guidance.
"""
from __future__ import annotations

from app.ai.llm.base import LLMProvider, Message


def _is_offline(llm: LLMProvider) -> bool:
    return getattr(llm, "name", "") == "stub"


async def _ask(llm: LLMProvider, system: str, user: str, temperature: float = 0.4) -> str | None:
    try:
        return (await llm.chat(
            [Message(role="system", content=system), Message(role="user", content=user)],
            temperature=temperature,
        )).strip()
    except Exception:
        return None


async def better_answer(llm: LLMProvider, question: str, answer: str, feedback: list[str]) -> str:
    if _is_offline(llm):
        tips = " ".join(feedback)
        return (
            "Improved answer (offline guidance): restate the question's intent, give a "
            "structured response (point → reason → concrete example with metrics), and close "
            f"with the outcome. Focus areas: {tips}"
        )
    out = await _ask(
        llm,
        "You are an expert interview coach. Rewrite the candidate's answer to be excellent: "
        "structured, specific, quantified, and confident. Keep it truthful to what they said.",
        f"Question: {question}\n\nCandidate answer: {answer}\n\nRewrite a stronger answer.",
    )
    return out or "Could not generate an improved answer at this time."


async def industry_standard_answer(llm: LLMProvider, question: str) -> str:
    if _is_offline(llm):
        return (
            "Industry-standard approach (offline): structure with context, your specific "
            "actions, the reasoning/trade-offs, and a measurable result; tie it back to the "
            "role's competencies."
        )
    out = await _ask(
        llm,
        "You are a senior interviewer. Provide a concise model answer that would score top "
        "marks for this question, suitable as a reference standard.",
        f"Question: {question}",
        temperature=0.3,
    )
    return out or "Reference answer unavailable."


async def recruiter_perspective(llm: LLMProvider, question: str, answer: str, score: int) -> str:
    if _is_offline(llm):
        verdict = "strong" if score >= 70 else "mixed" if score >= 45 else "weak"
        return (
            f"Recruiter view (offline): this reads as a {verdict} response ({score}/100). "
            "Recruiters look for clear ownership, structured storytelling, and measurable impact."
        )
    out = await _ask(
        llm,
        "You are a technical recruiter. In 2-3 sentences, give your honest hiring-signal read "
        "of this answer: what stands out and what would give you pause. Judge only the answer's "
        "content and delivery — never protected characteristics.",
        f"Question: {question}\n\nAnswer: {answer}\n\nDeterministic score: {score}/100.",
        temperature=0.3,
    )
    return out or "Recruiter perspective unavailable."
