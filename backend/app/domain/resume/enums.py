"""Resume / Job / ATS bounded-context enumerations."""
from __future__ import annotations

from enum import Enum


class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class ResumeSource(str, Enum):
    UPLOAD = "upload"
    AI_REWRITE = "ai_rewrite"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


# Canonical résumé sections an ATS expects. Used for section-coverage scoring.
class ResumeSection(str, Enum):
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"


# Heading aliases used to detect a section's presence in raw text.
SECTION_KEYWORDS: dict[ResumeSection, tuple[str, ...]] = {
    ResumeSection.SUMMARY: ("summary", "objective", "profile", "about"),
    ResumeSection.EXPERIENCE: (
        "experience",
        "employment",
        "work history",
        "professional experience",
    ),
    ResumeSection.EDUCATION: ("education", "academic", "qualifications"),
    ResumeSection.SKILLS: ("skills", "technical skills", "technologies", "tech stack"),
    ResumeSection.PROJECTS: ("projects", "personal projects", "portfolio"),
}
