"""Bounded file-like and streaming compression helpers."""

from __future__ import annotations

import bz2
import gzip
import lzma
import sys
from pathlib import Path

from .streaming import BoundedReadStream

DEFAULT_BUFFER_SIZE = 64 * 1024


class BoundedWriteStream:
    def __init__(self, stream, chunk_size=DEFAULT_BUFFER_SIZE):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.stream = stream
        self.chunk_size = chunk_size

    def write(self, data):
        total = 0
        for offset in range(0, len(data), self.chunk_size):
            total += self.stream.write(data[offset:offset + self.chunk_size])
        return total

    def flush(self):
        return self.stream.flush()

    def close(self):
        return self.stream.close()

    def __getattr__(self, name):
        return getattr(self.stream, name)


def _compression(path, compression):
    if compression:
        return compression.lstrip(".").lower()
    suffix = Path(path).suffix.lower() if isinstance(path, (str, Path)) else ""
    return suffix[1:] if suffix in (".gz", ".bz2", ".xz") else None


def open_input(source, *, compression=None, buffer_size=DEFAULT_BUFFER_SIZE):
    """Return ``(stream, owns_stream)`` for a path or file-like source."""
    owns = False
    if source is None or source == "-":
        raw = getattr(sys.stdin, "buffer", sys.stdin)
    elif hasattr(source, "read"):
        raw = source
    elif isinstance(source, (str, Path)):
        raw = Path(source).open("rb")
        owns = True
    else:
        raise TypeError("source must be a path or readable file-like object")
    bounded = BoundedReadStream(raw, buffer_size)
    kind = _compression(source, compression)
    if kind == "gz":
        return gzip.GzipFile(fileobj=bounded, mode="rb"), owns
    if kind == "bz2":
        return bz2.BZ2File(bounded, mode="rb"), owns
    if kind == "xz":
        return lzma.LZMAFile(bounded, mode="rb"), owns
    return bounded, owns


def open_output(destination, *, compression=None, buffer_size=DEFAULT_BUFFER_SIZE):
    """Return ``(stream, owns_stream)`` for a path or file-like destination."""
    owns = False
    if destination is None or destination == "-":
        raw = getattr(sys.stdout, "buffer", sys.stdout)
    elif hasattr(destination, "write"):
        raw = destination
    elif isinstance(destination, (str, Path)):
        raw = Path(destination).open("wb")
        owns = True
    else:
        raise TypeError("destination must be a path or writable file-like object")
    kind = _compression(destination, compression)
    if kind == "gz":
        return gzip.GzipFile(fileobj=raw, mode="wb"), owns
    if kind == "bz2":
        return bz2.BZ2File(raw, mode="wb"), owns
    if kind == "xz":
        return lzma.LZMAFile(raw, mode="wb"), owns
    return BoundedWriteStream(raw, buffer_size), owns
