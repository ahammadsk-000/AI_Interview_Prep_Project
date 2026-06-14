# Phase 8 — Observability

Cross-cutting instrumentation over every module. Status: **implemented**.

## Architecture
```
core/metrics.py            ← in-house Prometheus Counter/Gauge/Histogram + exposition
core/observability.py      ← ObservabilityMiddleware (trace id, http metrics, log correlation) + OTel hook
api/v1/endpoints/observability.py   ← GET /metrics
core/exceptions.py         ← unhandled-exception handler (logs + counts + safe 500)
ai/agents/tracing.py       ← flush_to_langfuse() (LLM-trace export behind the Phase-6 Tracer port)
services/agent_service.py  ← agent_runs_total metric + Langfuse forwarding
```

**Design choice — built-in core, exporters as config-gated swaps.** Metrics and request
tracing are dependency-free so `/metrics` works out of the box and is unit-testable.
OpenTelemetry (OTLP) and Langfuse load **lazily** only when enabled, so the platform is
fully observable locally and production-grade when the collectors are wired.

## What's instrumented
- **Metrics** (Prometheus text at `GET /metrics`): `http_requests_total{method,path,status}`,
  `http_request_duration_seconds` histogram, `http_requests_in_progress` gauge,
  `app_errors_total{type}`, `agent_runs_total{graph,status}`. Paths use the **route
  template** (not raw URLs) to bound cardinality.
- **Request tracing**: every request gets a W3C `trace_id` (propagated from an incoming
  `traceparent`) and a `request_id`, returned as response headers (`traceparent`,
  `X-Request-ID`).
- **Log correlation (Loki-ready)**: `trace_id`/`request_id`/`method`/`path` are bound to
  the structlog context, so every log line emitted during a request carries them — JSON
  in production for direct Loki/ELK ingestion.
- **Error tracking**: unhandled exceptions are logged with correlation ids, counted in
  `app_errors_total`, and returned as a generic 500 (no internals leaked).
- **Agent tracing → Langfuse**: each multi-agent run forwards its per-agent trace to
  Langfuse when configured, via the Phase-6 `Tracer` port — no vendor coupling in the
  orchestrator.

## Configuration (`.env`)
```
METRICS_ENABLED=true
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=prepforge-backend
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```
With OTel enabled and `opentelemetry-instrumentation-fastapi` installed, spans export to
the OTLP collector; with Langfuse keys set, agent traces appear in the Langfuse UI.

## Production topology
Prometheus scrapes `/metrics`; Grafana dashboards chart latency/error/throughput and
`agent_runs_total`. OTel Collector fans traces out to Tempo/Jaeger. Loki ingests the JSON
logs (correlated by `trace_id`). Langfuse captures LLM/agent traces with token + latency
cost. Alerting on `app_errors_total` rate and p99 of `http_request_duration_seconds`.

## Testing
- `tests/test_metrics.py` — counter/gauge/histogram math + Prometheus exposition format
  (HELP/TYPE lines, cumulative buckets, `+Inf`, `_sum`/`_count`).
- `tests/test_observability_api.py` — `X-Request-ID`/`traceparent` headers, incoming
  trace-id propagation, `/metrics` exposes HTTP metrics, unhandled-exception → safe 500 +
  `app_errors_total`, `agent_runs_total` incremented by a workflow run.
- **106 tests total green**; migrations unchanged (0001→0007).

## Security considerations
`/metrics` exposes only aggregate counters (no PII); restrict it to the internal network /
scrape target in production. Error responses never leak stack traces or messages. Trace
ids are random and carry no user data.

## Scalability considerations
In-process counters are per-replica; production scraping aggregates across replicas (or
swaps in `prometheus_client` multiprocess / OTel metrics). Tracing is sampled at the OTel
collector. Logging is async-friendly and structured for high-volume pipelines.
