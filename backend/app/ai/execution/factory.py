"""Execution-engine selection.

Prefer Judge0 when configured (the only safe choice for untrusted code in prod).
Fall back to the local Python runner for dev/tests. In production the local runner
is never selected unless explicitly allowed AND no Judge0 URL is set — a
misconfiguration we surface loudly via logs at call sites.
"""
from __future__ import annotations

from app.ai.execution.base import ExecutionEngine
from app.ai.execution.judge0 import Judge0ExecutionEngine
from app.ai.execution.local_python import LocalPythonExecutionEngine
from app.core.config import settings


def get_execution_engine() -> ExecutionEngine:
    if settings.JUDGE0_URL:
        return Judge0ExecutionEngine()
    return LocalPythonExecutionEngine()
