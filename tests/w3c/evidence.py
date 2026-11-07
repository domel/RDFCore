"""Resolve mapped pytest nodes; historical references remain unverified."""

from functools import lru_cache
from pathlib import Path
import subprocess
import sys

_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def _collected_nodes(path):
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "--color=no",
                "-o",
                "addopts=",
                path,
            ],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return frozenset()
    if result.returncode != 0:
        return frozenset()
    return frozenset(
        line.strip()
        for line in result.stdout.splitlines()
        if line.startswith(path + "::")
    )


def regression_evidence(historical, current=None):
    available = False
    if current:
        path, _, name = current.partition("::")
        source = (_ROOT / path).resolve()
        if source.is_file() and name and source.is_relative_to(_ROOT / "tests"):
            path = source.relative_to(_ROOT).as_posix()
            node = path + "::" + name
            available = any(
                actual == node or ("[" not in name and actual.startswith(node + "["))
                for actual in _collected_nodes(path)
            )
    return dict(
        evidence=current if available else None,
        historical_evidence=historical,
        verification_status="core-regression" if available else "unverified",
    )
