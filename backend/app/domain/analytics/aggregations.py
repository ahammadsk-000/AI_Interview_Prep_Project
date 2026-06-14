"""Pure aggregation helpers for the analytics dashboard.

Framework- and DB-free: they take plain (timestamp, value) series and produce
trend buckets and summaries. Bucketing happens in Python (not SQL date_trunc) so
the logic is portable across Postgres/SQLite and unit-testable.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.analytics.enums import Bucket


@dataclass
class TrendPoint:
    period: str
    value: float
    count: int


@dataclass
class Summary:
    count: int
    average: float
    minimum: float
    maximum: float
    first: float | None
    latest: float | None
    delta: float
    direction: str  # "up" | "down" | "flat"


def _period_key(ts: datetime, bucket: Bucket) -> str:
    if bucket == Bucket.WEEK:
        iso = ts.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return ts.strftime("%Y-%m-%d")


def bucket_series(points: list[tuple[datetime, float]], bucket: Bucket) -> list[TrendPoint]:
    """Average values within each day/week bucket, ordered chronologically."""
    grouped: dict[str, list[float]] = defaultdict(list)
    order: dict[str, datetime] = {}
    for ts, value in points:
        key = _period_key(ts, bucket)
        grouped[key].append(value)
        order.setdefault(key, ts)
    out = [
        TrendPoint(period=key, value=round(sum(vals) / len(vals), 2), count=len(vals))
        for key, vals in grouped.items()
    ]
    out.sort(key=lambda p: order[p.period])
    return out


def summarize(values: list[float]) -> Summary:
    if not values:
        return Summary(0, 0.0, 0.0, 0.0, None, None, 0.0, "flat")
    first, latest = values[0], values[-1]
    delta = round(latest - first, 2)
    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return Summary(
        count=len(values),
        average=round(sum(values) / len(values), 2),
        minimum=min(values),
        maximum=max(values),
        first=first,
        latest=latest,
        delta=delta,
        direction=direction,
    )


@dataclass
class DimensionBreakdown:
    averages: dict[str, int] = field(default_factory=dict)
    sample_size: int = 0


def average_dimensions(breakdowns: list[dict]) -> DimensionBreakdown:
    """Average per-dimension scores across many answer-grade breakdowns.

    Each breakdown is expected to carry ``{"dimensions": {name: score, ...}}``.
    """
    sums: dict[str, list[int]] = defaultdict(list)
    for b in breakdowns:
        dims = (b or {}).get("dimensions", {})
        for name, score in dims.items():
            if isinstance(score, (int, float)):
                sums[name].append(int(score))
    averages = {name: round(sum(v) / len(v)) for name, v in sums.items() if v}
    sample = max((len(v) for v in sums.values()), default=0)
    return DimensionBreakdown(averages=averages, sample_size=sample)
