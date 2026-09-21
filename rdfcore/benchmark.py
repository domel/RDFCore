"""Small benchmark harness for streaming RDF operations."""

from __future__ import annotations

import os
import platform
import time

try:
    import resource
except ImportError:  # pragma: no cover - Windows does not provide resource.
    resource = None

from .io import open_input
from .streaming import parse_stream


def benchmark_parse(source, format, *, buffer_size=64 * 1024, compression=None, **kwargs):
    """Measure a streaming parse and return comparable throughput metrics."""
    input_size = None
    if isinstance(source, (str, os.PathLike)) and os.path.exists(source):
        input_size = os.path.getsize(source)
    stream, owned = open_input(source, compression=compression, buffer_size=buffer_size)
    statements = 0

    class Sink:
        def add(self, statement):
            nonlocal statements
            statements += 1

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else 0
    started = time.perf_counter()
    try:
        parse_stream(stream, format, Sink(), **kwargs)
    finally:
        if owned:
            stream.close()
    elapsed = max(time.perf_counter() - started, 1e-12)
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else 0
    peak_rss = max(0, after - before)
    # Linux reports KiB, macOS bytes. Normalize the public metric to bytes.
    if peak_rss and platform.system() == "Darwin":
        peak_rss *= 1
    else:
        peak_rss *= 1024
    return {
        "input_bytes": input_size,
        "statements": statements,
        "elapsed_seconds": elapsed,
        "megabytes_per_second": (input_size / 1_000_000) / elapsed if input_size is not None else None,
        "statements_per_second": statements / elapsed,
        "peak_rss_bytes": peak_rss,
    }


__all__ = ["benchmark_parse"]
