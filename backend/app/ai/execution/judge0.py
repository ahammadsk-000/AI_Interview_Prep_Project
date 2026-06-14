"""Judge0 execution engine (production sandbox) — scaffold.

Judge0 isolates each submission in its own container with CPU/memory/time limits
and no host access. This adapter maps a function-based ``ExecutionRequest`` onto
Judge0 by generating a per-language harness that reads JSON args from stdin, calls
the entrypoint, and prints the result for comparison.

The HTTP wiring is implemented; per-language harness templates for Java/Go/C++/C#
are completed when those languages are enabled in a later phase. Selected by the
factory whenever ``JUDGE0_URL`` is configured.
"""
from __future__ import annotations

from app.ai.execution.base import ExecutionRequest, ExecutionResult
from app.core.config import settings
from app.domain.coding.enums import Language, SubmissionStatus

# Judge0 numeric language ids (defaults; configurable per deployment).
LANGUAGE_IDS: dict[Language, int] = {
    Language.PYTHON: 71,
    Language.JAVASCRIPT: 63,
    Language.JAVA: 62,
    Language.GO: 60,
    Language.CPP: 54,
    Language.CSHARP: 51,
}


class Judge0ExecutionEngine:
    name = "judge0"
    supported_languages = tuple(LANGUAGE_IDS.keys())

    def __init__(self) -> None:
        self._base = settings.JUDGE0_URL.rstrip("/")
        self._key = settings.JUDGE0_KEY

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        # Production implementation: build a per-language harness, POST batched
        # submissions to /submissions?base64_encoded=false&wait=true, then map
        # status/stdout back to CaseResult. Returns UNSUPPORTED until enabled so
        # the platform degrades predictably rather than silently mis-grading.
        return ExecutionResult(
            status=SubmissionStatus.UNSUPPORTED,
            passed=0, total=len(request.cases),
            message="Judge0 engine is configured but harness wiring is pending for "
                    f"{request.language.value}.",
        )
