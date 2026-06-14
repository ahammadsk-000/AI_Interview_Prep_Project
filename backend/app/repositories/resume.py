"""SQLAlchemy repositories for Resume, JobDescription, and AtsReport."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resume.enums import ResumeSource
from app.models.resume import AtsReport, JobDescription, Resume, ResumeVersion


class ResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, resume: Resume) -> Resume:
        self._s.add(resume)
        await self._s.flush()
        await self._s.refresh(resume, attribute_names=["created_at", "updated_at"])
        return resume

    async def get(self, id_: uuid.UUID) -> Resume | None:
        return await self._s.get(Resume, id_)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0):
        stmt = (
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def add_version(
        self, resume_id: uuid.UUID, *, content: dict, source: ResumeSource
    ) -> ResumeVersion:
        count = (
            await self._s.execute(
                select(func.count())
                .select_from(ResumeVersion)
                .where(ResumeVersion.resume_id == resume_id)
            )
        ).scalar_one()
        version = ResumeVersion(
            resume_id=resume_id, version=count + 1, content=content, source=source
        )
        self._s.add(version)
        await self._s.flush()
        return version


class JobDescriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, jd: JobDescription) -> JobDescription:
        self._s.add(jd)
        await self._s.flush()
        await self._s.refresh(jd, attribute_names=["created_at", "updated_at"])
        return jd

    async def get(self, id_: uuid.UUID) -> JobDescription | None:
        return await self._s.get(JobDescription, id_)


class AtsReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, report: AtsReport) -> AtsReport:
        self._s.add(report)
        await self._s.flush()
        await self._s.refresh(report, attribute_names=["created_at", "updated_at"])
        return report

    async def get(self, id_: uuid.UUID) -> AtsReport | None:
        return await self._s.get(AtsReport, id_)

    async def list_for_resume(self, resume_id: uuid.UUID):
        stmt = (
            select(AtsReport)
            .where(AtsReport.resume_id == resume_id)
            .order_by(AtsReport.created_at.desc())
        )
        return list((await self._s.execute(stmt)).scalars().all())
