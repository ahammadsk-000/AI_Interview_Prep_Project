"""Deterministic ATS / résumé scoring engine (framework-free domain logic).

Produces explainable 0–100 scores from rule-based signals — no LLM required, so
it is fast, reproducible, and unit-testable. The LLM layer (see ``app.ai``) adds
qualitative prose suggestions and rewrites *on top of* these scores; it never
replaces them.

Scores:
- ats_score        : machine parseability + keyword coverage
- recruiter_score  : human appeal (impact, structure, length)
- tech_score       : technical depth & breadth (and JD coverage when provided)
- comm_score       : communication quality (quantification, action verbs, bullets)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain.resume.enums import SECTION_KEYWORDS, ResumeSection
from app.domain.resume.skills import category_of, extract_skills

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")
_LINKEDIN_RE = re.compile(r"linkedin\.com/|github\.com/", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*•▪◦]\s+", re.MULTILINE)
_QUANTIFIED_RE = re.compile(r"\d+%|\$\s?\d+|\b\d+\s?x\b|\b\d{2,}\+?\b", re.IGNORECASE)

ACTION_VERBS = (
    "led", "built", "designed", "developed", "implemented", "improved", "reduced",
    "increased", "launched", "created", "architected", "optimized", "automated",
    "delivered", "managed", "scaled", "migrated", "deployed", "owned", "drove",
)

_TOTAL_SECTIONS = 6  # contact + 5 content sections


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _length_score(words: int) -> int:
    if words < 120:
        return _clamp(words / 120 * 55)          # too short
    if words <= 900:
        return 100                                # healthy 1–2 pages
    if words <= 1200:
        return 85
    return _clamp(85 - (words - 1200) / 40)       # too long


@dataclass
class AtsAnalysis:
    ats_score: int
    recruiter_score: int
    tech_score: int
    comm_score: int
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    breakdown: dict = field(default_factory=dict)

    @property
    def readiness(self) -> int:
        return _clamp(
            (self.ats_score + self.recruiter_score + self.tech_score + self.comm_score) / 4
        )


def analyze(resume_text: str, jd_skills: set[str] | None = None) -> AtsAnalysis:
    text = resume_text or ""
    low = text.lower()

    resume_skills = extract_skills(text)

    # ── contact & structure signals ──────────────────────────────────
    has_email = bool(_EMAIL_RE.search(text))
    has_phone = bool(_PHONE_RE.search(text))
    has_link = bool(_LINKEDIN_RE.search(text))

    sections = {ResumeSection.CONTACT: has_email or has_phone}
    for section, keywords in SECTION_KEYWORDS.items():
        sections[section] = any(kw in low for kw in keywords)
    sections_present = sum(1 for present in sections.values() if present)

    word_count = len(text.split())
    bullet_count = len(_BULLET_RE.findall(text))
    quantified = len(_QUANTIFIED_RE.findall(text))
    action_hits = sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", low))
    categories = {c for c in (category_of(s) for s in resume_skills) if c}

    # ── component scores (0–100) ─────────────────────────────────────
    section_score = _clamp(sections_present / _TOTAL_SECTIONS * 100)
    contact_score = _clamp(has_email * 60 + has_phone * 25 + has_link * 15)
    bullet_score = _clamp(bullet_count * 8)
    quantified_score = _clamp(quantified * 12)
    action_score = _clamp(action_hits * 12)
    length_score = _length_score(word_count)
    diversity_score = _clamp(len(categories) / 6 * 100)
    volume_score = _clamp(len(resume_skills) / 12 * 100)

    # ── keyword / JD match ───────────────────────────────────────────
    if jd_skills:
        required = set(jd_skills)
        matched = required & resume_skills
        missing = required - resume_skills
        keyword_match = _clamp(len(matched) / max(len(required), 1) * 100)
    else:
        matched = resume_skills
        missing = set()
        keyword_match = volume_score

    # ── headline scores ──────────────────────────────────────────────
    ats_score = _clamp(
        0.35 * section_score
        + 0.20 * contact_score
        + 0.35 * keyword_match
        + 0.10 * bullet_score
    )
    recruiter_score = _clamp(
        0.20 * section_score
        + 0.25 * quantified_score
        + 0.20 * action_score
        + 0.15 * bullet_score
        + 0.20 * length_score
    )
    if jd_skills:
        tech_score = _clamp(0.6 * keyword_match + 0.4 * diversity_score)
    else:
        tech_score = _clamp(0.5 * volume_score + 0.5 * diversity_score)
    comm_score = _clamp(
        0.30 * quantified_score
        + 0.25 * action_score
        + 0.20 * bullet_score
        + 0.25 * length_score
    )

    suggestions = _build_suggestions(
        sections=sections,
        has_email=has_email,
        has_phone=has_phone,
        has_link=has_link,
        quantified=quantified,
        action_hits=action_hits,
        word_count=word_count,
        missing=missing,
    )

    return AtsAnalysis(
        ats_score=ats_score,
        recruiter_score=recruiter_score,
        tech_score=tech_score,
        comm_score=comm_score,
        matched_keywords=sorted(matched),
        missing_keywords=sorted(missing),
        suggestions=suggestions,
        breakdown={
            "section_score": section_score,
            "contact_score": contact_score,
            "bullet_score": bullet_score,
            "quantified_score": quantified_score,
            "action_verb_score": action_score,
            "length_score": length_score,
            "skill_diversity_score": diversity_score,
            "keyword_match": keyword_match,
            "signals": {
                "word_count": word_count,
                "bullet_count": bullet_count,
                "quantified_mentions": quantified,
                "action_verbs": action_hits,
                "skills_found": len(resume_skills),
                "categories_covered": sorted(categories),
                "sections_present": [s.value for s, p in sections.items() if p],
            },
        },
    )


def _build_suggestions(
    *,
    sections: dict[ResumeSection, bool],
    has_email: bool,
    has_phone: bool,
    has_link: bool,
    quantified: int,
    action_hits: int,
    word_count: int,
    missing: set[str],
) -> list[str]:
    out: list[str] = []
    for section, present in sections.items():
        if not present and section is not ResumeSection.CONTACT:
            out.append(f"Add a clearly labeled '{section.value.title()}' section.")
    if not has_email:
        out.append("Add a professional email address to your contact details.")
    if not has_phone:
        out.append("Add a phone number so recruiters can reach you.")
    if not has_link:
        out.append("Include your LinkedIn and/or GitHub profile URL.")
    if quantified < 3:
        out.append("Quantify achievements with concrete metrics (%, $, counts, scale).")
    if action_hits < 5:
        out.append("Start bullet points with strong action verbs (led, built, reduced).")
    if word_count < 250:
        out.append("Resume looks thin — expand on impact, scope, and technologies used.")
    elif word_count > 1200:
        out.append("Resume is long — tighten to the most relevant 1–2 pages.")
    if missing:
        top = ", ".join(sorted(missing)[:10])
        out.append(f"Incorporate these job-relevant skills where truthful: {top}.")
    return out
