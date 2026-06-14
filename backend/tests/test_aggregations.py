"""Unit tests for the pure analytics aggregation helpers."""
from __future__ import annotations

from datetime import datetime

from app.domain.analytics.aggregations import (
    average_dimensions,
    bucket_series,
    summarize,
)
from app.domain.analytics.enums import Bucket


def test_summarize_direction_and_delta():
    s = summarize([40.0, 50.0, 70.0])
    assert s.count == 3
    assert s.first == 40.0 and s.latest == 70.0
    assert s.delta == 30.0
    assert s.direction == "up"
    assert s.average == 53.33

    assert summarize([]).direction == "flat"
    assert summarize([60.0, 50.0]).direction == "down"


def test_bucket_series_by_day():
    pts = [
        (datetime(2026, 6, 1, 9), 50.0),
        (datetime(2026, 6, 1, 18), 70.0),   # same day → averaged
        (datetime(2026, 6, 3, 10), 80.0),
    ]
    buckets = bucket_series(pts, Bucket.DAY)
    assert len(buckets) == 2
    assert buckets[0].period == "2026-06-01"
    assert buckets[0].value == 60.0 and buckets[0].count == 2
    assert buckets[1].value == 80.0


def test_bucket_series_by_week_orders_chronologically():
    pts = [
        (datetime(2026, 6, 1), 10.0),
        (datetime(2026, 6, 15), 30.0),
        (datetime(2026, 6, 8), 20.0),
    ]
    buckets = bucket_series(pts, Bucket.WEEK)
    values = [b.value for b in buckets]
    assert values == [10.0, 20.0, 30.0]


def test_average_dimensions():
    breakdowns = [
        {"dimensions": {"technical": 80, "communication": 60}},
        {"dimensions": {"technical": 60, "communication": 40}},
    ]
    d = average_dimensions(breakdowns)
    assert d.averages == {"technical": 70, "communication": 50}
    assert d.sample_size == 2
    assert average_dimensions([]).averages == {}
