"""AI Interviewer engine.

Generates the next interviewer question given conversation context. Uses the
``LLMProvider`` port for dynamic, context-aware questioning and follow-ups; falls
back to the curated bank when no model is reachable (offline/tests) so the flow
always works. Difficulty adapts to the candidate's last answer signal.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.ai.llm.base import LLMProvider, Message
from app.domain.interview.enums import Difficulty, InterviewType
from app.domain.interview.questions import (
    GENERIC_FOLLOW_UPS,
    questions_for,
    questions_for_skills,
)
from app.domain.interview.scoring import AnswerSignal


@dataclass
class QATurn:
    question: str
    answer: str | None = None


def adapt_difficulty(current: Difficulty, signal: AnswerSignal | None) -> Difficulty:
    """Raise difficulty after a strong answer, lower it after a weak one."""
    if signal is None:
        return current
    if signal.is_strong:
        return current.harder()
    if signal.is_weak:
        return current.easier()
    return current


class InterviewEngine:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def _system_prompt(self, interview_type: InterviewType, difficulty: Difficulty) -> str:
        return (
            f"You are an expert {interview_type.value.replace('_', ' ')} interviewer. "
            f"Ask ONE concise {difficulty.value} interview question at a time. "
            "Be context-aware: build on the candidate's previous answers with natural "
            "follow-ups. Ask only the question — no preamble, no commentary, no answer."
        )

    def _fallback_question(
        self,
        interview_type: InterviewType,
        difficulty: Difficulty,
        asked: set[str],
        last_signal: AnswerSignal | None,
        skills: list[str] | None = None,
    ) -> str:
        # A strong answer earns a deeper follow-up before the next fresh question.
        if last_signal is not None and last_signal.is_strong:
            for fu in GENERIC_FOLLOW_UPS:
                if fu not in asked:
                    return fu
        # 1) Résumé-tailored, technology-specific questions come first.
        for q in questions_for_skills(skills or []):
            if q not in asked:
                return q
        # 2) Then general questions for the interview type, difficulty-aware.
        pool = questions_for(interview_type)
        for want_match in (True, False):
            for diff, q in pool:
                if q in asked:
                    continue
                if want_match and diff != difficulty:
                    continue
                return q
        # 3) Finally, generic deepening follow-ups.
        for fu in GENERIC_FOLLOW_UPS:
            if fu not in asked:
                return fu
        return "Is there anything else you'd like to add about your experience?"

    async def next_question(
        self,
        *,
        interview_type: InterviewType,
        difficulty: Difficulty,
        history: list[QATurn],
        asked: set[str],
        last_signal: AnswerSignal | None = None,
        skills: list[str] | None = None,
    ) -> str:
        if getattr(self._llm, "name", "") == "stub":
            return self._fallback_question(interview_type, difficulty, asked, last_signal, skills)

        focus = f" Focus on the candidate's skills: {', '.join(skills)}." if skills else ""
        system = self._system_prompt(interview_type, difficulty) + focus
        messages = [Message(role="system", content=system)]
        for qa in history:
            messages.append(Message(role="assistant", content=qa.question))
            if qa.answer:
                messages.append(Message(role="user", content=qa.answer))
        if not history:
            messages.append(Message(role="user", content="Please begin the interview."))
        try:
            question = (await self._llm.chat(messages, temperature=0.6)).strip()
            if not question or question in asked:
                return self._fallback_question(interview_type, difficulty, asked, last_signal, skills)
            return question
        except Exception:
            return self._fallback_question(interview_type, difficulty, asked, last_signal, skills)

    async def summarize(self, history: list[QATurn], avg_score: int) -> str:
        if getattr(self._llm, "name", "") == "stub" or not history:
            answered = sum(1 for qa in history if qa.answer)
            return (
                f"Interview complete: {answered} question(s) answered. "
                f"Average answer-signal score {avg_score}/100. "
                "Detailed rubric grading and feedback are available via the evaluation module."
            )
        transcript = "\n".join(
            f"Q: {qa.question}\nA: {qa.answer or '(no answer)'}" for qa in history
        )
        try:
            return await self._llm.chat(
                [
                    Message(role="system", content="You are an interview coach. Summarize the "
                            "candidate's performance in 3-4 sentences: strengths, gaps, and one "
                            "concrete next step. Be specific and constructive."),
                    Message(role="user", content=transcript),
                ],
                temperature=0.3,
            )
        except Exception:
            return f"Interview complete. Average answer-signal score {avg_score}/100."
