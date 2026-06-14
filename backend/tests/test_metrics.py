"""Unit tests for the in-house Prometheus metrics primitives."""
from __future__ import annotations

from app.core.metrics import Counter, Gauge, Histogram, Registry


def test_counter_accumulates_per_label():
    c = Counter("jobs_total", "Jobs.", ("kind",))
    c.inc(kind="a")
    c.inc(2, kind="a")
    c.inc(kind="b")
    text = "\n".join(c.render())
    assert 'jobs_total{kind="a"} 3.0' in text
    assert 'jobs_total{kind="b"} 1.0' in text
    assert "# TYPE jobs_total counter" in text


def test_gauge_set_inc_dec():
    g = Gauge("inflight", "In flight.", ("m",))
    g.inc(m="GET")
    g.inc(m="GET")
    g.dec(m="GET")
    g.set(5, m="POST")
    text = "\n".join(g.render())
    assert 'inflight{m="GET"} 1.0' in text
    assert 'inflight{m="POST"} 5' in text


def test_histogram_buckets_and_sum():
    h = Histogram("lat", "Latency.", buckets=(0.1, 0.5, 1.0))
    h.observe(0.05)
    h.observe(0.3)
    h.observe(2.0)
    text = "\n".join(h.render())
    assert 'lat_bucket{le="0.1"} 1' in text     # only 0.05
    assert 'lat_bucket{le="0.5"} 2' in text     # 0.05, 0.3
    assert 'lat_bucket{le="+Inf"} 3' in text    # all three
    assert "lat_count" in text and "lat_sum" in text


def test_registry_render_includes_help_and_type():
    reg = Registry()
    reg.register(Counter("x_total", "An x counter."))
    out = reg.render()
    assert "# HELP x_total An x counter." in out
    assert "# TYPE x_total counter" in out
    assert out.endswith("\n")
