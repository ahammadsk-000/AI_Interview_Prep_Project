"""Local Python execution engine — DEV / TEST ONLY.

⚠️  SECURITY BOUNDARY  ⚠️
This runs the submitted Python in a child process with a wall-clock timeout. It is
NOT a security sandbox: it does not isolate the filesystem, network, or syscalls.
It exists so the platform is fully functional and testable on a developer machine.

In production, untrusted submissions MUST run on Judge0 / a Docker (gVisor/Firecracker)
sandbox. This engine refuses to run unless ``ALLOW_LOCAL_CODE_EXECUTION`` is true, and
the factory never selects it in a production environment.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.ai.execution.base import (
    CaseResult,
    ExecutionRequest,
    ExecutionResult,
)
from app.core.config import settings
from app.domain.coding.enums import Language, SubmissionStatus

# Runner executed in the child process. Reads cases.json, imports solution.py,
# runs each case, writes results.json. Kept dependency-free.
_RUNNER = r'''
import importlib.util, json, sys, time, traceback
from pathlib import Path

workdir = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("solution", workdir / "solution.py")
module = importlib.util.module_from_spec(spec)
results = {"status": "ok", "cases": []}
try:
    spec.loader.exec_module(module)
except Exception:
    (workdir / "results.json").write_text(json.dumps(
        {"status": "compile_error", "message": traceback.format_exc(limit=3), "cases": []}))
    sys.exit(0)

payload = json.loads((workdir / "cases.json").read_text())
fn = getattr(module, payload["entrypoint"], None)
if fn is None:
    (workdir / "results.json").write_text(json.dumps(
        {"status": "runtime_error",
         "message": "Entrypoint '%s' not found." % payload["entrypoint"], "cases": []}))
    sys.exit(0)

for case in payload["cases"]:
    t0 = time.perf_counter()
    try:
        out = fn(*case["args"])
        dt = (time.perf_counter() - t0) * 1000.0
        results["cases"].append({
            "index": case["index"], "passed": out == case["expected"],
            "is_hidden": case["is_hidden"], "runtime_ms": round(dt, 3), "error": None,
        })
    except Exception as exc:
        results["cases"].append({
            "index": case["index"], "passed": False, "is_hidden": case["is_hidden"],
            "runtime_ms": None, "error": "%s: %s" % (type(exc).__name__, exc),
        })
(workdir / "results.json").write_text(json.dumps(results))
'''


class LocalPythonExecutionEngine:
    name = "local_python"
    supported_languages = (Language.PYTHON,)

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if not settings.ALLOW_LOCAL_CODE_EXECUTION:
            return ExecutionResult(
                status=SubmissionStatus.UNSUPPORTED, passed=0, total=len(request.cases),
                message="Local code execution is disabled in this environment.",
            )
        if request.language != Language.PYTHON:
            return ExecutionResult(
                status=SubmissionStatus.UNSUPPORTED, passed=0, total=len(request.cases),
                message=f"Local engine supports Python only; got {request.language.value}. "
                        "Configure Judge0 for multi-language execution.",
            )

        return await asyncio.to_thread(self._run_sync, request)

    def _run_sync(self, request: ExecutionRequest) -> ExecutionResult:
        total = len(request.cases)
        with tempfile.TemporaryDirectory(prefix="prepforge_exec_") as tmp:
            work = Path(tmp)
            (work / "solution.py").write_text(request.source, encoding="utf-8")
            (work / "runner.py").write_text(_RUNNER, encoding="utf-8")
            (work / "cases.json").write_text(
                json.dumps(
                    {
                        "entrypoint": request.entrypoint,
                        "cases": [asdict(c) for c in request.cases],
                    }
                ),
                encoding="utf-8",
            )
            try:
                proc = subprocess.run(
                    [sys.executable, str(work / "runner.py"), str(work)],
                    capture_output=True, text=True, timeout=request.timeout_sec,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    status=SubmissionStatus.TIME_LIMIT, passed=0, total=total,
                    message=f"Execution exceeded {request.timeout_sec}s time limit.",
                )

            results_path = work / "results.json"
            if not results_path.exists():
                return ExecutionResult(
                    status=SubmissionStatus.RUNTIME_ERROR, passed=0, total=total,
                    message=(proc.stderr or "Execution failed with no output.")[:2000],
                )
            data = json.loads(results_path.read_text(encoding="utf-8"))

        if data["status"] != "ok":
            return ExecutionResult(
                status=SubmissionStatus.COMPILE_ERROR
                if data["status"] == "compile_error" else SubmissionStatus.RUNTIME_ERROR,
                passed=0, total=total, message=(data.get("message") or "")[:2000],
            )

        cases = [
            CaseResult(
                index=c["index"], passed=c["passed"], is_hidden=c["is_hidden"],
                runtime_ms=c["runtime_ms"], error=c["error"],
            )
            for c in data["cases"]
        ]
        passed = sum(1 for c in cases if c.passed)
        runtime = sum((c.runtime_ms or 0) for c in cases) or None
        status = (
            SubmissionStatus.ACCEPTED if passed == total and total > 0
            else SubmissionStatus.WRONG_ANSWER
        )
        # A case that raised is a runtime error overall (if nothing passed cleanly).
        if passed == 0 and any(c.error for c in cases):
            status = SubmissionStatus.RUNTIME_ERROR
        return ExecutionResult(
            status=status, passed=passed, total=total, cases=cases, runtime_ms=runtime,
        )
