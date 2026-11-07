"""Resolve mapped regressions; unmapped historical references remain unverified."""

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def regression_evidence(historical, current=None):
    available = False
    if current:
        path, _, name = current.partition("::")
        source = _ROOT / path
        if source.is_file() and name:
            available = any(
                isinstance(node, ast.FunctionDef) and node.name == name
                for node in ast.parse(source.read_text(encoding="utf-8")).body
            )
    return dict(
        evidence=current if available else None,
        historical_evidence=historical,
        verification_status="core-regression" if available else "unverified",
    )
