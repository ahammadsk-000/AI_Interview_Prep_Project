"""Code execution port (Dependency Inversion for the coding platform).

The submission pipeline depends on the ``ExecutionEngine`` Protocol, never on a
concrete sandbox. Production uses Judge0 / Docker isolation; dev/tests use a local
Python runner. Untrusted code MUST run in a sandbox — see ``local_python`` for the
explicit safety boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.domain.coding.enums import Language, SubmissionStatus


@dataclass
class TestCaseSpec:
    index: int
    args: list[Any]
    expected: Any
    is_hidden: bool = False
    weight: int = 1


@dataclass
class ExecutionRequest:
    language: Language
    source: str
    entrypoint: str
    cases: list[TestCaseSpec]
    timeout_sec: int = 8


@dataclass
class CaseResult:
    index: int
    passed: bool
    is_hidden: bool
    runtime_ms: float | None = None
    error: str | None = None


@dataclass
class ExecutionResult:
    status: SubmissionStatus
    passed: int
    total: int
    cases: list[CaseResult] = field(default_factory=list)
    runtime_ms: float | None = None
    memory_kb: int | None = None
    message: str | None = None

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed == self.total


@runtime_checkable
class ExecutionEngine(Protocol):
    name: str
    supported_languages: tuple[Language, ...]

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...
