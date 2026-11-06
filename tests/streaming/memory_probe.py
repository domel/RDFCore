"""Fresh-process RSS probe used only by streaming regression tests."""

import argparse
import json
import platform
import resource
import sys
from pathlib import Path
from time import perf_counter
from rdfcore.io import open_input
from rdfcore.pipeline import _close_stream
from rdfcore import external_sort

from rdfcore.streaming import parse_stream


def peak_rss():
    # ru_maxrss on Linux may include the parent's pre-exec address space.
    # VmHWM belongs to this exec's memory map and keeps heavy pytest parents
    # from masking the retained-record positive control.
    if sys.platform.startswith("linux"):
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("format")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--compression", choices=["gz", "bz2", "xz"])
    parser.add_argument("--operation", choices=["parse", "sort"], default="parse")
    parser.add_argument("--buffer-size", type=int, default=65536)
    parser.add_argument("--budget", type=int, default=65536)
    args = parser.parse_args()
    initial = peak_rss()
    started = perf_counter()

    class Counter:
        count = 0

        def add(self, statement):
            self.count += 1

    sink = Counter()
    source, owned = open_input(
        args.path, compression=args.compression, buffer_size=args.buffer_size
    )
    try:
        if args.operation == "sort":
            count = sum(
                1
                for _ in external_sort(
                    parse_stream(source, args.format),
                    memory_budget=args.budget,
                    max_open_runs=4,
                )
            )
        elif args.collect:
            records = []

            class Collector:
                def add(self, statement):
                    records.append(statement)

            parse_stream(source, args.format, Collector())
            count = len(records)
        else:
            parse_stream(source, args.format, sink)
            count = sink.count
    finally:
        _close_stream(source, owned)
    peak = peak_rss()
    print(
        json.dumps(
            {
                "statements": count,
                "peak_rss_bytes": peak,
                "input_file_bytes": Path(args.path).stat().st_size,
                "initial_rss_bytes": initial,
                "seconds": perf_counter() - started,
                "operation": args.operation,
                "collect": args.collect,
                "compression": args.compression,
                "buffer_size": args.buffer_size,
                "run_budget": args.budget,
                "python": platform.python_version(),
                "platform": sys.platform,
                "unit": "bytes",
            }
        )
    )


if __name__ == "__main__":
    main()
