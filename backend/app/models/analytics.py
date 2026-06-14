"""Analytics ORM model (Phase 7): MetricSnapshot.

A captured point-in-time metric (e.g. composite readiness) so trends survive even
as raw rows are archived. Designed to be partitioned by month at scale.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, uuid_pk


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    metric: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
