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


class _OwnedCodecStream:
    """Close an owned file even when closing its compression layer fails."""
    def __init__(self, stream, raw):
        self.stream, self.raw = stream, raw

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __iter__(self):
        return iter(self.stream)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        try:
            self.stream.close()
        finally:
            self.raw.close()


def _codec_stream(bounded, raw, owns, kind, mode):
    try:
        if kind == 'gz':
            stream = gzip.GzipFile(fileobj=bounded, mode=mode)
        elif kind == 'bz2':
            stream = bz2.BZ2File(bounded, mode=mode)
        elif kind == 'xz':
            stream = lzma.LZMAFile(bounded, mode=mode)
        else:
            return bounded, owns
    except BaseException:
        if owns:
            raw.close()
        raise
    return (_OwnedCodecStream(stream, raw) if owns else stream), owns


def _compression(path, compression):
    if compression:
        if not isinstance(compression, str):
            raise TypeError('compression must be a string')
        kind = compression.lstrip('.').lower()
        if kind not in ('gz', 'bz2', 'xz'):
            raise ValueError('unsupported compression')
        return kind
    suffix = Path(path).suffix.lower() if isinstance(path, (str, Path)) else ''
    return suffix[1:] if suffix in ('.gz', '.bz2', '.xz') else None


def open_input(source, *, compression=None, buffer_size=DEFAULT_BUFFER_SIZE):
    """Return ``(stream, owns_stream)`` for a path or file-like source."""
    _check_buffer_size(buffer_size)
    kind = _compression(source, compression)
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
    try:
        bounded = (_CompressionReadStream if kind in ('gz', 'bz2', 'xz') else BoundedReadStream)(raw, buffer_size)
        return _codec_stream(bounded, raw, owns, kind, 'rb')
    except BaseException:
        if owns:
            raw.close()
        raise


def open_output(destination, *, compression=None, buffer_size=DEFAULT_BUFFER_SIZE):
    """Return ``(stream, owns_stream)`` for a path or file-like destination."""
    _check_buffer_size(buffer_size)
    kind = _compression(destination, compression)
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
    bounded = BoundedWriteStream(raw, buffer_size)
    return _codec_stream(bounded, raw, owns, kind, 'wb')
