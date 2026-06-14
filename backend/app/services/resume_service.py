"""Resume / Job / ATS use-cases.

Orchestrates parsing, storage, the deterministic analyzer, and (optionally) the
LLM advisor. Enforces per-user ownership: a resource owned by another user is
reported as *not found* (avoids existence leakage).
"""
from __future__ import annotations

import uuid

from app.ai.llm.base import LLMProvider, Message
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.resume.analyzer import AtsAnalysis, analyze
from app.domain.resume.enums import ResumeSource, ResumeStatus
from app.domain.resume.skills import extract_skills
from app.models.resume import AtsReport, JobDescription, Resume
from app.repositories.resume import (
    AtsReportRepository,
    JobDescriptionRepository,
    ResumeRepository,
)
from app.schemas.resume import JobDescriptionCreate, OptimizeRequest
from app.services.parsing.document_parser import (
    extract_text,
    mime_for,
    safe_filename,
    validate_upload,
)
from app.services.storage import FileStorage


class ResumeService:
    def __init__(self, resumes: ResumeRepository, storage: FileStorage) -> None:
        self._resumes = resumes
        self._storage = storage

    async def create_from_upload(
        self, *, user_id: uuid.UUID, filename: str, content: bytes
    ) -> Resume:
        file_type = validate_upload(filename, content)
        clean_name = safe_filename(filename)
        text = extract_text(content, file_type)

        storage_key = self._storage.save(
            namespace=str(user_id), filename=clean_name, content=content
        )
        resume = Resume(
            user_id=user_id,
            filename=clean_name,
            storage_key=storage_key,
            mime=mime_for(filename),
            parsed_text=text,
            status=ResumeStatus.PARSED if text else ResumeStatus.FAILED,
        )
        return await self._resumes.add(resume)

    async def get_owned(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume:
        resume = await self._resumes.get(resume_id)
        if resume is None or resume.user_id != user_id:
            raise NotFoundError("Resume not found.")
        return resume

    async def list_for_user(self, user_id: uuid.UUID, **kw) -> list[Resume]:
        return await self._resumes.list_for_user(user_id, **kw)


class JobService:
    def __init__(self, jobs: JobDescriptionRepository) -> None:
        self._jobs = jobs

    async def create(self, user_id: uuid.UUID, data: JobDescriptionCreate) -> JobDescription:
        skills = sorted(extract_skills(data.raw_text))
        jd = JobDescription(
            user_id=user_id,
            title=data.title,
            company=data.company,
            raw_text=data.raw_text,
            extracted_skills=skills,
        )
        return await self._jobs.add(jd)

    async def get_owned(self, jd_id: uuid.UUID, user_id: uuid.UUID) -> JobDescription:
        jd = await self._jobs.get(jd_id)
        if jd is None or jd.user_id != user_id:
            raise NotFoundError("Job description not found.")
        return jd


class AtsService:
    def __init__(
        self,
        resumes: ResumeService,
        jobs: JobService,
        reports: AtsReportRepository,
        llm: LLMProvider,
        resume_repo: ResumeRepository,
    ) -> None:
        self._resumes = resumes
        self._jobs = jobs
        self._reports = reports
        self._llm = llm
        self._resume_repo = resume_repo

    async def _resolve_jd_skills(
        self, *, user_id: uuid.UUID, jd_id: uuid.UUID | None, jd_text: str | None
    ) -> tuple[set[str] | None, uuid.UUID | None]:
        if jd_id is not None:
            jd = await self._jobs.get_owned(jd_id, user_id)
            return set(jd.extracted_skills or []), jd.id
        if jd_text:
            return extract_skills(jd_text), None
        return None, None

    async def analyze(
        self,
        *,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        jd_id: uuid.UUID | None = None,
        jd_text: str | None = None,
    ) -> AtsReport:
        resume = await self._resumes.get_owned(resume_id, user_id)
        if not resume.parsed_text:
            raise ValidationError("Resume has no extractable text to analyze.")

        jd_skills, resolved_jd_id = await self._resolve_jd_skills(
            user_id=user_id, jd_id=jd_id, jd_text=jd_text
        )
        result = analyze(resume.parsed_text, jd_skills)
        report = AtsReport(
            resume_id=resume.id,
            job_description_id=resolved_jd_id,
            ats_score=result.ats_score,
            recruiter_score=result.recruiter_score,
            tech_score=result.tech_score,
            comm_score=result.comm_score,
            matched_keywords=result.matched_keywords,
            missing_keywords=result.missing_keywords,
            suggestions=result.suggestions,
            breakdown=result.breakdown,
        )
        return await self._reports.add(report)

    async def optimize(self, user_id: uuid.UUID, req: OptimizeRequest):
        resume = await self._resumes.get_owned(req.resume_id, user_id)
        if not resume.parsed_text:
            raise ValidationError("Resume has no extractable text to optimize.")

        jd_skills, resolved_jd_id = await self._resolve_jd_skills(
            user_id=user_id, jd_id=req.job_description_id, jd_text=req.jd_text
        )
        result = analyze(resume.parsed_text, jd_skills)
        report = await self._reports.add(
            AtsReport(
                resume_id=resume.id,
                job_description_id=resolved_jd_id,
                ats_score=result.ats_score,
                recruiter_score=result.recruiter_score,
                tech_score=result.tech_score,
                comm_score=result.comm_score,
                matched_keywords=result.matched_keywords,
                missing_keywords=result.missing_keywords,
                suggestions=result.suggestions,
                breakdown=result.breakdown,
            )
        )
        improved = await self._rewrite(resume.parsed_text, result)
        # Persist the rewrite as a new resume version (résumé version control).
        await self._resume_repo.add_version(
            resume.id,
            content={"text": improved, "based_on_report": str(report.id)},
            source=ResumeSource.AI_REWRITE,
        )
        insights = self._recruiter_insights(result)
        return report, result, improved, insights

    async def _rewrite(self, resume_text: str, result: AtsAnalysis) -> str:
        """LLM-backed rewrite; deterministic annotation when offline (stub)."""
        if getattr(self._llm, "name", "") == "stub":
            return self._deterministic_rewrite(resume_text, result)
        prompt = (
            "Rewrite the following resume to be more ATS-friendly and impactful. "
            "Keep all facts truthful; do not invent experience. Use strong action "
            "verbs, quantify achievements, and naturally incorporate these missing "
            f"job-relevant skills where appropriate: {', '.join(result.missing_keywords) or 'none'}.\n\n"
            f"RESUME:\n{resume_text}"
        )
        try:
            return await self._llm.chat(
                [
                    Message(role="system", content="You are an expert technical resume writer."),
                    Message(role="user", content=prompt),
                ]
            )
        except Exception:
            return self._deterministic_rewrite(resume_text, result)

    @staticmethod
    def _deterministic_rewrite(resume_text: str, result: AtsAnalysis) -> str:
        header = ["# Optimization notes (auto-generated, offline mode)"]
        if result.missing_keywords:
            header.append(
                "Recommended skills to incorporate where truthful: "
                + ", ".join(result.missing_keywords)
            )
        header.extend(f"- {s}" for s in result.suggestions)
        return "\n".join(header) + "\n\n---\n\n" + resume_text

    @staticmethod
    def _recruiter_insights(result: AtsAnalysis) -> list[str]:
        insights: list[str] = []
        insights.append(
            f"Overall interview-readiness: {result.readiness}/100 "
            f"(ATS {result.ats_score}, recruiter {result.recruiter_score}, "
            f"technical {result.tech_score}, communication {result.comm_score})."
        )
        if result.missing_keywords:
            insights.append(
                f"{len(result.missing_keywords)} job-relevant skills are missing or not surfaced."
            )
        insights.extend(result.suggestions[:5])
        return insights
