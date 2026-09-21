"""Small Python compatibility helpers used by later parser stages."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import Any, TypeVar

PY3 = sys.version_info[0] == 3
text_type = str
binary_type = bytes
string_types = (str,)

T = TypeVar("T")


def reraise(exception: BaseException) -> None:
    """Raise *exception* while keeping a helper-compatible call site."""

    raise exception


def from_n3(value: T) -> T:
    """Compatibility identity hook retained for parser integration points."""

    return value


def is_py3() -> bool:
    return PY3


def iteritems(mapping: dict[Any, T]) -> Iterator[tuple[Any, T]]:
    return iter(mapping.items())
