"""Resume upload & retrieval, job descriptions, and ATS analysis/optimization."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.v1.deps import AtsSvc, CurrentUser, JobSvc, ResumeSvc
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.schemas.resume import (
    AnalyzeRequest,
    AtsReportPublic,
    JobDescriptionCreate,
    JobDescriptionPublic,
    OptimizeRequest,
    OptimizeResponse,
    ResumePublic,
)

router = APIRouter(tags=["resume"])


# ── Resumes ─────────────────────────────────────────────────────────
@router.post("/resumes", response_model=ResumePublic, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    current: CurrentUser, resumes: ResumeSvc, file: UploadFile = File(...)
) -> ResumePublic:
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("File exceeds the upload size limit.")
    resume = await resumes.create_from_upload(
        user_id=current.id, filename=file.filename or "resume", content=content
    )
    return ResumePublic.from_orm_resume(resume)


@router.get("/resumes", response_model=list[ResumePublic])
async def list_resumes(
    current: CurrentUser,
    resumes: ResumeSvc,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ResumePublic]:
    records = await resumes.list_for_user(current.id, limit=limit, offset=offset)
    return [ResumePublic.from_orm_resume(r) for r in records]


@router.get("/resumes/{resume_id}", response_model=ResumePublic)
async def get_resume(
    resume_id: uuid.UUID, current: CurrentUser, resumes: ResumeSvc
) -> ResumePublic:
    resume = await resumes.get_owned(resume_id, current.id)
    return ResumePublic.from_orm_resume(resume)


@router.post("/resumes/{resume_id}/analyze", response_model=AtsReportPublic)
async def analyze_resume(
    resume_id: uuid.UUID, payload: AnalyzeRequest, current: CurrentUser, ats: AtsSvc
) -> AtsReportPublic:
    report = await ats.analyze(
        user_id=current.id,
        resume_id=resume_id,
        jd_id=payload.job_description_id,
        jd_text=payload.jd_text,
    )
    return AtsReportPublic.from_orm_report(report)


# ── Job descriptions ────────────────────────────────────────────────
@router.post(
    "/job-descriptions",
    response_model=JobDescriptionPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_description(
    payload: JobDescriptionCreate, current: CurrentUser, jobs: JobSvc
) -> JobDescriptionPublic:
    jd = await jobs.create(current.id, payload)
    return JobDescriptionPublic.model_validate(jd)


# ── ATS optimization ────────────────────────────────────────────────
@router.post("/ats/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    payload: OptimizeRequest, current: CurrentUser, ats: AtsSvc
) -> OptimizeResponse:
    report, result, improved, insights = await ats.optimize(current.id, payload)
    return OptimizeResponse(
        ats_compatibility=result.ats_score,
        missing_keywords=result.missing_keywords,
        recruiter_insights=insights,
        improved_resume_text=improved,
        report=AtsReportPublic.from_orm_report(report),
    )
