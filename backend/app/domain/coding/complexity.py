"""Static time/space complexity estimation.

A heuristic estimator — not a proof. For Python it uses the AST (loop nesting,
recursion, sorting); for other languages it falls back to regex heuristics. Good
enough to give candidates an interview-readiness signal and flag obvious
quadratic/exponential solutions; clearly labelled as an estimate to callers.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from app.domain.coding.enums import ComplexityClass, Language

_SORT_CALLS = ("sorted", "sort")
_NESTED_LOOP_RE = re.compile(r"\bfor\b|\bwhile\b")


@dataclass
class ComplexityEstimate:
    time: ComplexityClass
    space: ComplexityClass
    notes: list[str]


def estimate(source: str, language: Language, entrypoint: str | None = None) -> ComplexityEstimate:
    if language == Language.PYTHON:
        try:
            return _estimate_python(source, entrypoint)
        except SyntaxError:
            pass
    return _estimate_regex(source)


# ── Python AST estimator ────────────────────────────────────────────
class _LoopDepthVisitor(ast.NodeVisitor):
    def __init__(self, func_names: set[str]) -> None:
        self.func_names = func_names
        self.max_depth = 0
        self._depth = 0
        self.has_sort = False
        self.recursive_calls = 0
        self.allocates_collection = False

    def _enter_loop(self, node: ast.AST) -> None:
        self._depth += 1
        self.max_depth = max(self.max_depth, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    visit_For = _enter_loop
    visit_While = _enter_loop
    visit_AsyncFor = _enter_loop

    def visit_Call(self, node: ast.Call) -> None:
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name in _SORT_CALLS:
            self.has_sort = True
        if name in self.func_names:
            self.recursive_calls += 1
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.allocates_collection = True
        self.generic_visit(node)

    visit_DictComp = visit_ListComp
    visit_SetComp = visit_ListComp


def _estimate_python(source: str, entrypoint: str | None) -> ComplexityEstimate:
    tree = ast.parse(source)
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    visitor = _LoopDepthVisitor(func_names)
    visitor.visit(tree)
    notes: list[str] = []

    # Time
    if visitor.recursive_calls >= 2 and visitor.max_depth == 0:
        time = ComplexityClass.O_2N
        notes.append("Multiple recursive calls without memoization suggest exponential time.")
    elif visitor.max_depth >= 3:
        time = ComplexityClass.O_N3
    elif visitor.max_depth == 2:
        time = ComplexityClass.O_N2
        notes.append("Nested loops detected (≈O(n^2)); check if it can be reduced.")
    elif visitor.max_depth == 1:
        time = ComplexityClass.O_N_LOG_N if visitor.has_sort else ComplexityClass.O_N
    elif visitor.has_sort:
        time = ComplexityClass.O_N_LOG_N
    elif visitor.recursive_calls == 1:
        time = ComplexityClass.O_N
    else:
        time = ComplexityClass.O_1

    # Space (rough): collection allocation or recursion implies non-constant space.
    if visitor.allocates_collection or visitor.recursive_calls >= 1:
        space = ComplexityClass.O_N
    else:
        space = ComplexityClass.O_1
    return ComplexityEstimate(time=time, space=space, notes=notes)


# ── Regex fallback (non-Python) ─────────────────────────────────────
def _estimate_regex(source: str) -> ComplexityEstimate:
    loops = len(_NESTED_LOOP_RE.findall(source))
    has_sort = bool(re.search(r"\.sort\b|sorted\(|Arrays\.sort|std::sort", source))
    if loops >= 2:
        time = ComplexityClass.O_N2
    elif loops == 1:
        time = ComplexityClass.O_N_LOG_N if has_sort else ComplexityClass.O_N
    elif has_sort:
        time = ComplexityClass.O_N_LOG_N
    else:
        time = ComplexityClass.O_1
    return ComplexityEstimate(
        time=time, space=ComplexityClass.UNKNOWN,
        notes=["Estimate from text heuristics (non-Python language)."],
    )
