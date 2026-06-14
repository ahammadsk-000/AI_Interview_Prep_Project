"""Integration tests for observability: /metrics, request-id, error handling."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_and_traceparent_headers(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
    assert resp.headers.get("traceparent", "").startswith("00-")


@pytest.mark.asyncio
async def test_incoming_traceparent_is_propagated(client: AsyncClient):
    incoming = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
    resp = await client.get("/health", headers={"traceparent": incoming})
    # The 32-hex trace id is preserved across the response.
    assert ("a" * 32) in resp.headers.get("traceparent", "")


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_http_metrics(client: AsyncClient):
    await client.get("/health")  # generate at least one request
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds_bucket" in body
    assert "# TYPE http_requests_total counter" in body


@pytest.mark.asyncio
async def test_unhandled_exception_is_tracked(error_client: AsyncClient):
    resp = await error_client.get("/_debug/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    # No internal details leaked.
    assert "intentional test failure" not in resp.text
    # The error counter is now present in the exposition.
    metrics = (await error_client.get("/metrics")).text
    assert "app_errors_total" in metrics
    assert 'type="RuntimeError"' in metrics


@pytest.mark.asyncio
async def test_agent_run_metric_incremented(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/agents/career-readiness", headers=auth_headers,
        json={"target_role": "ML Engineer", "resume_text": "Python FastAPI Kubernetes engineer."},
    )
    metrics = (await client.get("/metrics")).text
    assert "agent_runs_total" in metrics
    assert 'graph="career_readiness"' in metrics
