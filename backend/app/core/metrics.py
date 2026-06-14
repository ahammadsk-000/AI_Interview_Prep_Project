"""Minimal, dependency-free Prometheus metrics.

Implements Counter / Gauge / Histogram and the Prometheus text exposition format.
Kept in-house so the platform exposes `/metrics` with zero external deps and is
unit-testable; ``prometheus_client`` / OTel metric exporters are a drop-in for
multi-process production scraping (documented in the observability module).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

_LabelKey = tuple[tuple[str, str], ...]


def _key(labels: dict[str, str]) -> _LabelKey:
    return tuple(sorted(labels.items()))


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _fmt_labels(key: _LabelKey, extra: dict[str, str] | None = None) -> str:
    pairs = list(key)
    if extra:
        pairs = sorted({**dict(key), **extra}.items())
    if not pairs:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in pairs)
    return "{" + inner + "}"


class _Lockable:
    def __init__(self) -> None:
        self._lock = threading.Lock()


class Counter(_Lockable):
    def __init__(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.name, self.help, self.labelnames = name, help, labelnames
        self._values: dict[_LabelKey, float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._values[_key(labels)] = self._values.get(_key(labels), 0.0) + amount

    def render(self) -> list[str]:
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        for key, val in self._values.items():
            out.append(f"{self.name}{_fmt_labels(key)} {val}")
        return out


class Gauge(_Lockable):
    def __init__(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.name, self.help, self.labelnames = name, help, labelnames
        self._values: dict[_LabelKey, float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._values[_key(labels)] = self._values.get(_key(labels), 0.0) + amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        self.inc(-amount, **labels)

    def set(self, value: float, **labels: str) -> None:
        with self._lock:
            self._values[_key(labels)] = value

    def render(self) -> list[str]:
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} gauge"]
        for key, val in self._values.items():
            out.append(f"{self.name}{_fmt_labels(key)} {val}")
        return out


_DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


@dataclass
class _HistCell:
    buckets: dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0


class Histogram(_Lockable):
    def __init__(
        self, name: str, help: str, labelnames: tuple[str, ...] = (),
        buckets: tuple[float, ...] = _DEFAULT_BUCKETS,
    ) -> None:
        super().__init__()
        self.name, self.help, self.labelnames = name, help, labelnames
        self.buckets = buckets
        self._cells: dict[_LabelKey, _HistCell] = {}

    def observe(self, value: float, **labels: str) -> None:
        with self._lock:
            cell = self._cells.setdefault(_key(labels), _HistCell())
            cell.sum += value
            cell.count += 1
            # Each bucket holds the cumulative count of observations with value <= le.
            for b in self.buckets:
                if value <= b:
                    cell.buckets[b] = cell.buckets.get(b, 0) + 1

    def render(self) -> list[str]:
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} histogram"]
        for key, cell in self._cells.items():
            for b in self.buckets:
                out.append(
                    f"{self.name}_bucket{_fmt_labels(key, {'le': _num(b)})} "
                    f"{cell.buckets.get(b, 0)}"
                )
            out.append(f"{self.name}_bucket{_fmt_labels(key, {'le': '+Inf'})} {cell.count}")
            out.append(f"{self.name}_sum{_fmt_labels(key)} {cell.sum}")
            out.append(f"{self.name}_count{_fmt_labels(key)} {cell.count}")
        return out


def _num(b: float) -> str:
    return str(int(b)) if b == int(b) else str(b)


class Registry:
    def __init__(self) -> None:
        self._metrics: list = []

    def register(self, metric):
        self._metrics.append(metric)
        return metric

    def render(self) -> str:
        lines: list[str] = []
        for m in self._metrics:
            lines.extend(m.render())
        return "\n".join(lines) + "\n"


# ── Default registry + the app's metric instruments ─────────────────
registry = Registry()

http_requests_total = registry.register(
    Counter("http_requests_total", "Total HTTP requests.", ("method", "path", "status"))
)
http_request_duration_seconds = registry.register(
    Histogram("http_request_duration_seconds", "HTTP request latency.", ("method", "path"))
)
http_requests_in_progress = registry.register(
    Gauge("http_requests_in_progress", "In-flight HTTP requests.", ("method",))
)
app_errors_total = registry.register(
    Counter("app_errors_total", "Unhandled application errors.", ("type",))
)
agent_runs_total = registry.register(
    Counter("agent_runs_total", "Multi-agent workflow runs.", ("graph", "status"))
)

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
