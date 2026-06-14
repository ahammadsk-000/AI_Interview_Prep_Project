"""The seven PrepForge agents.

Each agent reuses the deterministic domain engines built in earlier phases (resume
analyzer, ATS matcher, interview question bank, DSA complexity/quality, behavioral
grader) and contributes a slice of the shared blackboard. The Feedback and Career-
Coach agents synthesize everything; they optionally use the LLM for prose with a
deterministic fallback.
"""
from __future__ import annotations

from app.ai.agents.base import AgentContext, AgentResult
from app.ai.llm.base import Message
from app.domain.agents.enums import AgentName, role_to_interview_type
from app.domain.coding.complexity import estimate as estimate_complexity
from app.domain.coding.enums import Language
from app.domain.coding.quality import assess as assess_quality
from app.domain.evaluation.grader import grade_behavioral
from app.domain.interview.questions import questions_for
from app.domain.resume.analyzer import analyze as analyze_resume
from app.domain.resume.skills import extract_skills


class ResumeAgent:
    name = AgentName.RESUME

    def applies(self, ctx: AgentContext) -> bool:
        return ctx.has("resume_text")

    async def run(self, ctx: AgentContext) -> AgentResult:
        r = analyze_resume(ctx.inputs["resume_text"])
        value = {
            "ats_score": r.ats_score, "recruiter_score": r.recruiter_score,
            "tech_score": r.tech_score, "comm_score": r.comm_score,
            "readiness": r.readiness, "suggestions": r.suggestions[:5],
            "skills_found": r.breakdown.get("signals", {}).get("skills_found", 0),
        }
        ctx.memory["resume_tech_score"] = r.tech_score
        return AgentResult(key="resume", value=value,
                           summary=f"Resume analyzed — readiness {r.readiness}/100.")


class AtsAgent:
    name = AgentName.ATS

    def applies(self, ctx: AgentContext) -> bool:
        return ctx.has("resume_text", "jd_text")

    async def run(self, ctx: AgentContext) -> AgentResult:
        jd_skills = extract_skills(ctx.inputs["jd_text"])
        r = analyze_resume(ctx.inputs["resume_text"], jd_skills)
        value = {
            "compatibility": r.ats_score,
            "matched_keywords": r.matched_keywords,
            "missing_keywords": r.missing_keywords,
        }
        return AgentResult(key="ats", value=value,
                           summary=f"ATS match {r.ats_score}% vs job description; "
                                   f"{len(r.missing_keywords)} keywords missing.")


class InterviewerAgent:
    name = AgentName.INTERVIEWER

    def applies(self, ctx: AgentContext) -> bool:
        return ctx.has("target_role") or ctx.has("resume_text")

    async def run(self, ctx: AgentContext) -> AgentResult:
        itype = role_to_interview_type(ctx.inputs.get("target_role"))
        seed = [q for _d, q in questions_for(itype)][:5]
        value = {"interview_type": itype.value, "recommended_questions": seed}
        return AgentResult(key="interview_plan", value=value,
                           summary=f"Prepared a {itype.value} interview plan "
                                   f"({len(seed)} focus questions).")


class CodingEvaluatorAgent:
    name = AgentName.CODING_EVALUATOR

    def applies(self, ctx: AgentContext) -> bool:
        return ctx.has("code")

    async def run(self, ctx: AgentContext) -> AgentResult:
        lang = Language(ctx.inputs.get("language", "python"))
        source = ctx.inputs["code"]
        comp = estimate_complexity(source, lang)
        qual = assess_quality(source, lang)
        value = {
            "time_complexity": comp.time.value, "space_complexity": comp.space.value,
            "code_quality": qual.score, "notes": (comp.notes + qual.notes)[:5],
        }
        ctx.memory["code_quality"] = qual.score
        return AgentResult(key="coding", value=value,
                           summary=f"Static code review — {comp.time.value} time, "
                                   f"quality {qual.score}/100.")


class BehavioralEvaluatorAgent:
    name = AgentName.BEHAVIORAL

    def applies(self, ctx: AgentContext) -> bool:
        return ctx.has("behavioral_answer")

    async def run(self, ctx: AgentContext) -> AgentResult:
        g = grade_behavioral(ctx.inputs["behavioral_answer"])
        value = {
            "score": g.total,
            "competencies": {c.value: v for c, v in g.competencies.items()},
            "missing_star": [c.value for c in g.star.missing],
        }
        ctx.memory["behavioral_score"] = g.total
        return AgentResult(key="behavioral", value=value,
                           summary=f"Behavioral answer scored {g.total}/100 "
                                   f"(STAR {g.star.score}/100).")


class FeedbackAgent:
    """Synthesizes all prior agent outputs into a unified readiness verdict."""

    name = AgentName.FEEDBACK

    def applies(self, ctx: AgentContext) -> bool:
        return bool(ctx.outputs)  # runs whenever at least one agent produced output

    async def run(self, ctx: AgentContext) -> AgentResult:
        signals: dict[str, int] = {}
        out = ctx.outputs
        if "resume" in out:
            signals["resume"] = out["resume"]["readiness"]
            signals["technical"] = out["resume"]["tech_score"]
        if "ats" in out:
            signals["ats_match"] = out["ats"]["compatibility"]
        if "coding" in out:
            signals["coding_quality"] = out["coding"]["code_quality"]
        if "behavioral" in out:
            signals["behavioral"] = out["behavioral"]["score"]

        overall = round(sum(signals.values()) / len(signals)) if signals else 0
        strengths = [f"{k} ({v}/100)" for k, v in signals.items() if v >= 70]
        improvements = [k for k, v in signals.items() if v < 55]
        value = {
            "overall_readiness": overall,
            "signals": signals,
            "strengths": strengths,
            "improvements": improvements,
            "summary": (
                f"Overall interview readiness {overall}/100 across "
                f"{len(signals)} signal(s)."
                + (f" Strong: {', '.join(strengths)}." if strengths else "")
                + (f" Needs work: {', '.join(improvements)}." if improvements else "")
            ),
        }
        return AgentResult(key="feedback", value=value,
                           summary=f"Synthesized feedback — readiness {overall}/100.")


_ACTION_LIBRARY = {
    "technical": "Build and ship a project using the target stack; add metrics to your resume.",
    "resume": "Rewrite bullets with action verbs and quantified impact; run the ATS optimizer.",
    "ats_match": "Tailor your resume to the job description's keywords (truthfully).",
    "coding_quality": "Practice DSA daily; refactor for clarity and optimal complexity.",
    "behavioral": "Rehearse STAR-structured stories with measurable outcomes.",
}


class CareerCoachAgent:
    """Turns weaknesses into a concrete, personalized action plan."""

    name = AgentName.CAREER_COACH

    def applies(self, ctx: AgentContext) -> bool:
        return "feedback" in ctx.outputs

    async def run(self, ctx: AgentContext) -> AgentResult:
        fb = ctx.outputs["feedback"]
        focus = [
            {"area": area, "action": _ACTION_LIBRARY.get(area, "Targeted practice and review.")}
            for area in fb["improvements"]
        ] or [{"area": "polish", "action": "Maintain momentum with weekly mock interviews."}]

        summary_text = await self._coach_summary(ctx, fb)
        value = {
            "focus_areas": focus,
            "target_interview_type": ctx.outputs.get("interview_plan", {}).get("interview_type"),
            "summary": summary_text,
        }
        return AgentResult(key="career_plan", value=value,
                           summary=f"Built a {len(focus)}-area action plan.")

    async def _coach_summary(self, ctx: AgentContext, fb: dict) -> str:
        role = ctx.inputs.get("target_role") or "your target role"
        if getattr(ctx.llm, "name", "") == "stub":
            return (
                f"To get interview-ready for {role}, prioritize: "
                + (", ".join(fb["improvements"]) if fb["improvements"]
                   else "consistency — you're tracking well")
                + f". Current readiness {fb['overall_readiness']}/100."
            )
        try:
            return (await ctx.llm.chat([
                Message(role="system", content="You are a supportive, concrete career coach."),
                Message(role="user", content=(
                    f"Target role: {role}. Readiness {fb['overall_readiness']}/100. "
                    f"Weak areas: {fb['improvements']}. Give a 3-sentence action plan.")),
            ], temperature=0.4)).strip()
        except Exception:
            return f"Focus on {', '.join(fb['improvements']) or 'consistency'} for {role}."


def career_readiness_agents() -> list:
    """Ordered agent pipeline for the career-readiness workflow."""
    return [
        ResumeAgent(), AtsAgent(), InterviewerAgent(), CodingEvaluatorAgent(),
        BehavioralEvaluatorAgent(), FeedbackAgent(), CareerCoachAgent(),
    ]
