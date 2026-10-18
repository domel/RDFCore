"""Bounded file-like and streaming compression helpers."""

from __future__ import annotations

import bz2
import gzip
import lzma
import sys
from pathlib import Path

from .streaming import BoundedReadStream

DEFAULT_BUFFER_SIZE = 64 * 1024


def _check_buffer_size(value):
    if not isinstance(value, int):
        raise TypeError('buffer size must be an integer')
    if value <= 0:
        raise ValueError('buffer size must be positive')


class _CompressionReadStream(BoundedReadStream):
    """Fill codec requests while keeping each underlying read bounded.

    In particular gzip's two-byte magic check does not tolerate a short read.
    The codec, rather than the input buffer size, controls this small buffer.
    """

    def read(self, size=-1):
        if size < 0:
            return super().read(size)
        parts = []
        remaining = size
        while remaining:
            part = super().read(remaining)
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        return b''.join(parts)


class BoundedWriteStream:
    def __init__(self, stream, chunk_size=DEFAULT_BUFFER_SIZE):
        _check_buffer_size(chunk_size)
        self.stream = stream
        self.chunk_size = chunk_size

    def write(self, data):
        total = 0
        for offset in range(0, len(data), self.chunk_size):
            chunk = data[offset:offset + self.chunk_size]
            while chunk:
                written = self.stream.write(chunk)
                if not isinstance(written, int) or not 0 < written <= len(chunk):
                    raise OSError('output stream did not report valid write progress')
                total += written
                chunk = chunk[written:]
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
    _check_buffer_size(buffer_size)
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
    kind = _compression(source, compression)
    bounded = (_CompressionReadStream if kind in ('gz', 'bz2', 'xz') else BoundedReadStream)(raw, buffer_size)
    if kind == "gz":
        return gzip.GzipFile(fileobj=bounded, mode="rb"), owns
    if kind == "bz2":
        return bz2.BZ2File(bounded, mode="rb"), owns
    if kind == "xz":
        return lzma.LZMAFile(bounded, mode="rb"), owns
    return bounded, owns


def open_output(destination, *, compression=None, buffer_size=DEFAULT_BUFFER_SIZE):
    """Return ``(stream, owns_stream)`` for a path or file-like destination."""
    _check_buffer_size(buffer_size)
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
    bounded = BoundedWriteStream(raw, buffer_size)
    if kind == "gz":
        return gzip.GzipFile(fileobj=bounded, mode="wb"), owns
    if kind == "bz2":
        return bz2.BZ2File(bounded, mode="wb"), owns
    if kind == "xz":
        return lzma.LZMAFile(bounded, mode="wb"), owns
    return bounded, owns
