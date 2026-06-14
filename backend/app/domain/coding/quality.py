"""Static code-quality scoring (0–100) with actionable notes.

Language-agnostic heuristics with a Python AST pass for structure. Rewards
decomposition, docstrings/comments, and readable naming; penalizes giant
functions, deep nesting, and bare excepts.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from app.domain.coding.enums import Language

_SNAKE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass
class QualityReport:
    score: int
    notes: list[str]


def assess(source: str, language: Language) -> QualityReport:
    if language == Language.PYTHON:
        try:
            return _assess_python(source)
        except SyntaxError:
            return QualityReport(score=0, notes=["Code does not parse."])
    return _assess_generic(source)


def _assess_python(source: str) -> QualityReport:
    tree = ast.parse(source)
    notes: list[str] = []
    score = 100

    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    lines = source.splitlines()
    loc = len([line for line in lines if line.strip()])

    # Function length / decomposition.
    for fn in funcs:
        length = (fn.end_lineno or fn.lineno) - fn.lineno
        if length > 60:
            score -= 15
            notes.append(f"Function '{fn.name}' is long ({length} lines); consider splitting.")
        if ast.get_docstring(fn) is None and length > 12:
            score -= 5
            notes.append(f"Add a docstring to '{fn.name}' explaining intent and complexity.")

    # Naming.
    bad_names = [
        fn.name for fn in funcs if not _SNAKE_RE.match(fn.name) and fn.name != fn.name.lower()
    ]
    if bad_names:
        score -= 8
        notes.append("Use snake_case for function names: " + ", ".join(bad_names))

    # Bare excepts.
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            score -= 10
            notes.append("Avoid bare 'except:'; catch specific exceptions.")
            break

    # Comment density (light touch).
    comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
    if loc > 25 and comment_lines == 0:
        score -= 5
        notes.append("Add a few comments to explain non-obvious logic.")

    # Deep nesting.
    if _max_indent(lines) >= 5:
        score -= 8
        notes.append("Deep nesting detected; flatten with early returns or helpers.")

    return QualityReport(score=max(0, min(100, score)), notes=notes)


def _assess_generic(source: str) -> QualityReport:
    lines = source.splitlines()
    loc = len([line for line in lines if line.strip()])
    score = 100
    notes: list[str] = []
    if loc > 120:
        score -= 15
        notes.append("Solution is long; consider decomposing into helpers.")
    if _max_indent(lines) >= 6:
        score -= 10
        notes.append("Deep nesting detected; flatten control flow.")
    if not any("//" in line or "/*" in line for line in lines) and loc > 30:
        score -= 5
        notes.append("Add comments for non-obvious logic.")
    return QualityReport(score=max(0, min(100, score)), notes=notes)


def _max_indent(lines: list[str]) -> int:
    depth = 0
    for line in lines:
        if not line.strip():
            continue
        spaces = len(line) - len(line.lstrip(" "))
        depth = max(depth, spaces // 4)
    return depth
