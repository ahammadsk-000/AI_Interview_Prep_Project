"""Unit tests for the deterministic ATS analyzer + skills taxonomy (Module 2/3)."""
from __future__ import annotations

from app.domain.resume.analyzer import analyze
from app.domain.resume.skills import extract_skills

STRONG_RESUME = """
Jane Doe
jane.doe@example.com | +1 415 555 0199 | linkedin.com/in/janedoe | github.com/janedoe

Summary
Senior Machine Learning Engineer with 6 years building production GenAI systems.

Experience
- Led a team that built a RAG platform using Python, FastAPI, LangChain and pgvector,
  reducing support resolution time by 40%.
- Designed and deployed Kubernetes microservices on AWS, improving throughput 3x.
- Implemented CI/CD with GitHub Actions and automated 200+ tests.

Skills
Python, PyTorch, TensorFlow, Docker, Kubernetes, PostgreSQL, Redis, FastAPI, LangGraph

Education
B.Tech in Computer Science, IIT.

Projects
- Built an LLM evaluation harness with vector databases and Prometheus monitoring.
"""

WEAK_RESUME = "I am a person who likes computers and did some work somewhere."


def test_extract_skills_finds_canonical_names():
    skills = extract_skills(STRONG_RESUME)
    assert {"Python", "FastAPI", "Kubernetes", "PyTorch", "LangChain", "AWS"} <= skills


def test_extract_skills_word_boundaries():
    # "Go" must not match inside "Google"; bare text without the skill stays empty.
    assert "Go" not in extract_skills("I work at Google on search.")
    assert "Go" in extract_skills("Backend services written in Go and Rust.")


def test_strong_resume_scores_high():
    r = analyze(STRONG_RESUME)
    assert r.ats_score >= 70
    assert r.tech_score >= 70
    assert r.recruiter_score >= 60
    assert 0 <= r.readiness <= 100


def test_weak_resume_scores_low_and_has_suggestions():
    r = analyze(WEAK_RESUME)
    assert r.ats_score < 50
    assert r.suggestions  # actionable guidance produced
    # Missing standard sections should be called out.
    assert any("section" in s.lower() for s in r.suggestions)


def test_jd_matching_reports_missing_keywords():
    jd_skills = {"Python", "Kubernetes", "Go", "Terraform"}
    r = analyze(STRONG_RESUME, jd_skills)
    assert "Python" in r.matched_keywords
    assert "Kubernetes" in r.matched_keywords
    # Go/Terraform are absent from the resume -> flagged missing.
    assert "Terraform" in r.missing_keywords
    assert "Go" in r.missing_keywords


def test_scores_are_bounded_ints():
    for text in (STRONG_RESUME, WEAK_RESUME, ""):
        r = analyze(text)
        for score in (r.ats_score, r.recruiter_score, r.tech_score, r.comm_score):
            assert isinstance(score, int)
            assert 0 <= score <= 100
