"""Fresh-process large RDF measurements; run manually, never in each PR.

python -m benchmarks.large_data --sizes 100000 1000000 --output results.json
Each timed run gets a new interpreter. Validation is outside the timer.
"""

from __future__ import annotations
import argparse
import hashlib
import itertools
import math
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter

FORMATS = {"nt": "nt", "nq": "nquads", "ttl": "turtle", "trig": "trig"}
OPERATIONS = ("parse", "write", "sqlite", "query", "sort", "compare")


def generate(path, size, format):
    digest = hashlib.sha256()
    with path.open("wb") as stream:
        for index in range(size):
            triple = f'<urn:s{index}> <urn:p{index % 7}> "{index}"'
            graph = f"<urn:g{index % 3}>" if index % 4 else None
            line = (
                triple + " " + graph + " .\n"
                if format == "nq" and graph
                else graph + " { " + triple + " . }\n"
                if format == "trig" and graph
                else triple + " .\n"
            )
            data = line.encode()
            stream.write(data)
            digest.update(data)
    return digest.hexdigest()


def rss():
    if sys.platform.startswith("linux"):
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def verify_rows(statements, size, dataset, default=None):
    seen = bytearray(size)
    for statement in statements:
        s, p, o = statement[:3]
        index = int(str(s).removeprefix("urn:s"))
        assert 0 <= index < size and not seen[index]
        seen[index] = 1
        assert str(p) == f"urn:p{index % 7}" and str(o) == str(index)
        assert type(s).__name__ == "URIRef" and type(p).__name__ == "URIRef"
        assert (
            type(o).__name__ == "Literal" and o.language is None and o.datatype is None
        )
        if dataset:
            context = getattr(statement[3], "identifier", statement[3])
            context = None if context == default else context
            assert (str(context) if context is not None else None) == (
                f"urn:g{index % 3}" if index % 4 else None
            )
    assert all(seen)


def verify(graph, size, dataset):
    assert len(graph) == size
    verify_rows(
        graph.quads() if dataset else graph,
        size,
        dataset,
        graph.default_graph.identifier if dataset else None,
    )


def verify_stream(path, format, size, dataset, *, ordered=False):
    from rdfcore import parse_stream, statement_key

    class Validator:
        def __init__(self):
            self.seen = bytearray(size)
            self.previous = None

        def add(self, statement):
            s, p, o = statement[:3]
            index = int(str(s).removeprefix("urn:s"))
            assert 0 <= index < size and not self.seen[index]
            self.seen[index] = 1
            assert str(p) == f"urn:p{index % 7}" and str(o) == str(index)
            assert type(s).__name__ == "URIRef" and type(p).__name__ == "URIRef"
            assert (
                type(o).__name__ == "Literal"
                and o.language is None
                and o.datatype is None
            )
            if dataset:
                context = statement[3] if len(statement) == 4 else None
                assert (str(context) if context is not None else None) == (
                    f"urn:g{index % 3}" if index % 4 else None
                )
            if ordered:
                key = statement_key(statement)
                assert self.previous is None or self.previous <= key
                self.previous = key

    validator = Validator()
    parse_stream(path, format, validator)
    assert all(validator.seen)


def worker(args):
    import rdflib, rdfcore
    from rdfcore.compare import isomorphic

    module = rdflib if args.library == "rdflib" else rdfcore
    dataset = args.format in ("nq", "trig")
    format = FORMATS[args.format]
    result = {}
    peak = 0
    if args.operation == "parse":
        if args.library == "stream":

            class FingerprintSink:
                amount = 0
                fingerprint = 0

                def add(self, statement):
                    signature = tuple(
                        (
                            type(term).__name__,
                            str(term),
                            str(term.datatype)
                            if getattr(term, "datatype", None) is not None
                            else None,
                            getattr(term, "language", None),
                            getattr(term, "direction", None),
                        )
                        if term is not None
                        else None
                        for term in statement
                    )
                    self.amount += 1
                    self.fingerprint += int.from_bytes(
                        hashlib.blake2b(
                            repr(signature).encode(), digest_size=16
                        ).digest(),
                        "big",
                    )

            sink = FingerprintSink()
            started = perf_counter()
            rdfcore.parse_stream(args.input, format, sink)
            elapsed = perf_counter() - started
            peak = rss()
            assert sink.amount == args.size
            expected = 0
            for index in range(args.size):
                signature = (
                    ("URIRef", f"urn:s{index}", None, None, None),
                    ("URIRef", f"urn:p{index % 7}", None, None, None),
                    ("Literal", str(index), None, None, None),
                )
                if dataset and (args.format == "nq" or index % 4):
                    context = (
                        ("URIRef", f"urn:g{index % 3}", None, None, None)
                        if index % 4
                        else None
                    )
                    signature = (*signature, context)
                expected += int.from_bytes(
                    hashlib.blake2b(repr(signature).encode(), digest_size=16).digest(),
                    "big",
                )
            assert sink.fingerprint == expected
            result["timing_includes"] = "parsing and bounded semantic fingerprint sink"
            result["verification"] = (
                "exact count and aggregate 128-bit semantic fingerprints"
            )
            graph = None
        else:
            graph = module.Dataset() if dataset else module.Graph()
            started = perf_counter()
            graph.parse(args.input, format=format)
            elapsed = perf_counter() - started
            peak = rss()
        if graph is not None:
            verify(graph, args.size, dataset)
    elif args.operation == "write":
        output = Path(args.directory) / "output.rdf"
        if args.library == "stream":
            factories = {
                "nt": rdfcore.NTStreamingWriter,
                "nq": rdfcore.NQStreamingWriter,
                "ttl": rdfcore.TurtleStreamingWriter,
                "trig": rdfcore.TriGStreamingWriter,
            }
            options = {"default_graph_id": None} if dataset else {}
            with output.open("wb") as stream:
                writer = factories[args.format](stream, **options)
                started = perf_counter()
                for index in range(args.size):
                    row = (
                        rdfcore.URIRef(f"urn:s{index}"),
                        rdfcore.URIRef(f"urn:p{index % 7}"),
                        rdfcore.Literal(str(index)),
                    )
                    if dataset:
                        row = (
                            *row,
                            rdfcore.URIRef(f"urn:g{index % 3}") if index % 4 else None,
                        )
                    writer.add(row)
                writer.close()
            elapsed = perf_counter() - started
            result["timing_includes"] = (
                "term construction, serialization and file writes"
            )
        else:
            graph = (module.Dataset() if dataset else module.Graph()).parse(
                args.input, format=format
            )
            started = perf_counter()
            graph.serialize(destination=output, format=format)
            elapsed = perf_counter() - started
            result["timing_includes"] = (
                "serialization and file writes; graph setup excluded"
            )
        peak = rss()
        verify_stream(output, format, args.size, dataset)
    elif args.operation == "sqlite":
        store = rdfcore.SQLiteStore(Path(args.directory) / "data.sqlite")

        def rows():
            for i in range(args.size):
                yield (
                    rdfcore.URIRef(f"urn:s{i}"),
                    rdfcore.URIRef(f"urn:p{i % 7}"),
                    rdfcore.Literal(str(i)),
                )

        started = perf_counter()
        amount = store.add_many(rows(), rdfcore.URIRef("urn:g"))
        elapsed = perf_counter() - started
        peak = rss()
        assert amount == args.size
        store.close()
        store = rdfcore.SQLiteStore(Path(args.directory) / "data.sqlite")
        graph = rdfcore.Graph(store=store, identifier=rdfcore.URIRef("urn:g"))
        verify(graph, args.size, False)
        store.close()
    elif args.operation == "query":
        graph = module.Graph()
        for i in range(args.size):
            graph.add(
                (
                    module.URIRef(f"urn:s{i}"),
                    module.URIRef(f"urn:p{i % 7}"),
                    module.Literal(str(i)),
                )
            )
        verify(graph, args.size, False)
        target = module.URIRef("urn:s0"), module.URIRef("urn:p0"), module.Literal("0")
        patterns = [
            tuple(t if b else None for t, b in zip(target, bound))
            for bound in itertools.product((False, True), repeat=3)
        ]
        # Derive exact expected results before timing, without normalizing terms.
        expected = [
            {
                row
                for row in graph
                if all(v is None or v == t for v, t in zip(pattern, row))
            }
            for pattern in patterns
        ]
        counts, pattern_seconds = [], []
        for pattern in patterns:
            started = perf_counter()
            counts.append(sum(1 for _ in graph.triples(pattern)))
            pattern_seconds.append(perf_counter() - started)
        elapsed = sum(pattern_seconds)
        peak = rss()
        assert counts == [len(rows) for rows in expected]
        for pattern, rows in zip(patterns, expected):
            assert set(graph.triples(pattern)) == rows
        result["patterns"] = [
            {"bound": [v is not None for v in p], "matches": n, "seconds": seconds}
            for p, n, seconds in zip(patterns, counts, pattern_seconds)
        ]
    elif args.operation == "sort":
        from rdfcore import (
            external_sort,
            parse_stream,
            NTStreamingWriter,
        )

        output = Path(args.directory) / "sorted.nt"
        with output.open("wb") as stream:
            writer = NTStreamingWriter(stream)
            started = perf_counter()
            for row in external_sort(
                parse_stream(args.input, format),
                memory_budget=args.budget,
                max_open_runs=8,
                temp_dir=args.directory,
            ):
                writer.add(row[:3])
            writer.close()
            elapsed = perf_counter() - started
        peak = rss()
        verify_stream(output, "nt", args.size, False, ordered=True)
        assert not list(Path(args.directory).glob("rdfcore-run-*"))
    else:
        # Symmetric cycle: bounded separately from the large parse workload.
        n = min(args.size, args.compare_nodes)
        graphs = [module.Graph(), module.Graph()]
        for j, g in enumerate(graphs):
            for i in range(n):
                g.add(
                    (
                        module.BNode(f"{j}-{i}"),
                        module.URIRef("urn:p"),
                        module.BNode(f"{j}-{(i + 1) % n}"),
                    )
                )
        assert all(len(graph) == n for graph in graphs)
        function = (
            __import__("rdflib.compare", fromlist=["isomorphic"]).isomorphic
            if args.library == "rdflib"
            else isomorphic
        )
        started = perf_counter()
        answer = function(*graphs)
        elapsed = perf_counter() - started
        peak = rss()
        assert answer
        graphs[1].remove((None, None, None))
        assert not function(*graphs)
        result["compare_nodes"] = n
    return {
        "seconds": elapsed,
        "statements_per_second": args.size / elapsed
        if args.operation not in ("query", "compare")
        else None,
        "work_units": n
        if args.operation == "compare"
        else 8
        if args.operation == "query"
        else args.size,
        "work_unit": "nodes"
        if args.operation == "compare"
        else "queries"
        if args.operation == "query"
        else "statements",
        "peak_rss_bytes": peak,
        "correctness_verified": True,
        **result,
    }


def write_report(path, report):
    """Keep the last complete checkpoint readable if a run is interrupted."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(json.dumps(report, indent=2) + "\n")
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def regression_checks(current, baseline, margin=0.25):
    """Relative guard derived from baseline samples; never a universal SLA."""
    for field in (
        "python",
        "platform",
        "machine",
        "cpu_count",
        "cpu_affinity",
        "cpu_model",
        "rdflib",
        "run_budget",
        "warmup",
    ):
        if current.get(field) != baseline.get(field):
            raise ValueError(f"incompatible baseline {field}")

    def key(row):
        return tuple(
            row[field]
            for field in ("size", "format", "operation", "library", "dataset_sha256")
        )

    expected = {
        key(row): row for row in baseline["results"] if row["status"] == "passed"
    }
    checks = []
    for row in current["results"]:
        if row["status"] != "passed":
            continue
        old = expected.get(key(row))
        if old is None or len(old["samples"]) < 3 or len(row["samples"]) < 3:
            raise ValueError("matching baseline and three samples are required")
        values = [sample["seconds"] for sample in old["samples"]]
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("invalid baseline samples")
        median = statistics.median(values)
        deviation = statistics.median(abs(value - median) for value in values)
        limit = median + max(6 * deviation, median * margin)
        checks.append(
            {
                "case": list(key(row)),
                "limit_seconds": limit,
                "median_seconds": row["median_seconds"],
                "passed": row["median_seconds"] <= limit,
            }
        )
        if row["operation"] == "query":
            for bound in itertools.product((False, True), repeat=3):

                def times(entry):
                    values = []
                    for sample in entry["samples"]:
                        matches = [
                            pattern["seconds"]
                            for pattern in sample.get("patterns", [])
                            if tuple(pattern["bound"]) == bound
                        ]
                        if (
                            len(matches) != 1
                            or not math.isfinite(matches[0])
                            or matches[0] <= 0
                        ):
                            raise ValueError(
                                "baseline and current query samples require per-pattern timings"
                            )
                        values.append(matches[0])
                    return values

                previous, measured = times(old), times(row)
                center = statistics.median(previous)
                noise = statistics.median(abs(value - center) for value in previous)
                limit = center + max(6 * noise, center * margin)
                observed = statistics.median(measured)
                checks.append(
                    {
                        "case": list(key(row)),
                        "bound": list(bound),
                        "limit_seconds": limit,
                        "median_seconds": observed,
                        "passed": observed <= limit,
                    }
                )
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[100000, 1000000])
    parser.add_argument(
        "--formats", choices=list(FORMATS), nargs="+", default=list(FORMATS)
    )
    parser.add_argument(
        "--operations", choices=OPERATIONS, nargs="+", default=list(OPERATIONS)
    )
    parser.add_argument(
        "--libraries",
        choices=["rdflib", "rdfcore", "stream"],
        nargs="+",
        default=["rdflib", "rdfcore", "stream"],
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--budget", type=int, default=4 * 1024**2)
    parser.add_argument("--compare-nodes", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--regression-margin", type=float, default=0.25)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--size", type=int)
    parser.add_argument("--format", choices=list(FORMATS))
    parser.add_argument("--library", choices=["rdflib", "rdfcore", "stream"])
    parser.add_argument("--operation", choices=OPERATIONS)
    parser.add_argument("--directory")
    args = parser.parse_args()
    if (
        args.repeats < 1
        or args.warmup < 0
        or min(args.sizes) < 1
        or args.budget < 1
        or args.timeout <= 0
        or args.compare_nodes < 3
        or args.regression_margin < 0
        or not math.isfinite(args.regression_margin)
        or not math.isfinite(args.timeout)
    ):
        parser.error("invalid measurement limits")
    if args.worker:
        print(json.dumps(worker(args)))
        return
    baseline = None
    if args.baseline:
        same = args.baseline.resolve() == args.output.resolve()
        if args.output.exists() and args.baseline.exists():
            same = same or os.path.samefile(args.baseline, args.output)
        if same:
            parser.error("baseline and output must refer to different files")
        baseline = json.loads(args.baseline.read_text())
    import rdflib

    report = {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "python": platform.python_version(),
        "rdflib": rdflib.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "repeats": args.repeats,
        "warmup": args.warmup,
        "timeout": args.timeout,
        "timeout_scope": "entire worker, including setup and correctness verification",
        "run_budget": args.budget,
        "measurement": "fresh process per warmup/sample; RSS high-water at timing end, includes setup; correctness outside timing; sort includes NT output",
        "results": [],
    }
    from rdfcore import __version__

    report["rdfcore"] = __version__
    report["tracked_diff_sha256"] = hashlib.sha256(
        subprocess.check_output(["git", "diff", "HEAD", "--binary"])
    ).hexdigest()
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], text=True
    ).splitlines()
    report["untracked_source_sha256"] = {
        name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
        for name in untracked
        if name.endswith(".py")
    }
    report["cpu_affinity"] = (
        len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    )
    report["load_average"] = os.getloadavg() if hasattr(os, "getloadavg") else None
    report["memory_total_kib"] = (
        next(
            (
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemTotal:")
            ),
            None,
        )
        if Path("/proc/meminfo").exists()
        else None
    )
    report["cpu_model"] = (
        next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            platform.processor(),
        )
        if Path("/proc/cpuinfo").exists()
        else platform.processor()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    failed = False
    with tempfile.TemporaryDirectory(prefix="rdfcore-large-") as temporary:
        root = Path(temporary)
        for size in args.sizes:
            for format in args.formats:
                path = root / f"{size}.{format}"
                sha = generate(path, size, format)
                for operation in args.operations:
                    if operation == "compare" and size != args.sizes[0]:
                        continue
                    for library in args.libraries:
                        if library == "stream" and operation not in ("parse", "write"):
                            continue
                        if operation in ("sqlite", "sort") and (
                            library != "rdfcore" or format != "nt"
                        ):
                            continue
                        if operation in ("query", "compare") and format != "nt":
                            continue
                        case_size = (
                            min(size, args.compare_nodes)
                            if operation == "compare"
                            else size
                        )
                        case_hash = (
                            hashlib.sha256(
                                f"directed-cycle-v1:{case_size}".encode()
                            ).hexdigest()
                            if operation == "compare"
                            else sha
                        )
                        entry = {
                            "size": case_size,
                            "format": format,
                            "operation": operation,
                            "library": library,
                            "dataset_sha256": case_hash,
                            "input_bytes": None
                            if operation == "compare"
                            else path.stat().st_size,
                            "samples": [],
                            "status": "running",
                        }
                        report["results"].append(entry)
                        write_report(args.output, report)
                        for index in range(args.warmup + args.repeats):
                            with tempfile.TemporaryDirectory(dir=root) as directory:
                                command = [
                                    sys.executable,
                                    "-m",
                                    "benchmarks.large_data",
                                    "--worker",
                                    "--input",
                                    str(path),
                                    "--size",
                                    str(size),
                                    "--format",
                                    format,
                                    "--library",
                                    library,
                                    "--operation",
                                    operation,
                                    "--directory",
                                    directory,
                                    "--budget",
                                    str(args.budget),
                                    "--compare-nodes",
                                    str(args.compare_nodes),
                                ]
                                try:
                                    result = subprocess.run(
                                        command,
                                        text=True,
                                        capture_output=True,
                                        timeout=args.timeout,
                                        check=True,
                                    )
                                    record = json.loads(result.stdout)
                                    if (
                                        record.get("correctness_verified") is not True
                                        or not math.isfinite(
                                            record.get("seconds", float("nan"))
                                        )
                                        or record["seconds"] <= 0
                                        or record.get("peak_rss_bytes", 0) <= 0
                                    ):
                                        raise ValueError(
                                            "invalid worker measurement or missing verification"
                                        )
                                    if index >= args.warmup:
                                        entry["samples"].append(record)
                                    write_report(args.output, report)
                                except (
                                    subprocess.SubprocessError,
                                    ValueError,
                                    KeyError,
                                    TypeError,
                                ) as error:
                                    failed = True
                                    entry["status"] = "failed"
                                    entry["error"] = str(error)
                                    if isinstance(error, subprocess.CalledProcessError):
                                        entry["stderr"] = error.stderr
                                    break
                        else:
                            entry["status"] = "passed"
                            entry["median_seconds"] = statistics.median(
                                r["seconds"] for r in entry["samples"]
                            )
                            entry["median_statements_per_second"] = (
                                size / entry["median_seconds"]
                                if operation not in ("query", "compare")
                                else None
                            )
                            entry["max_rss_bytes"] = max(
                                r["peak_rss_bytes"] for r in entry["samples"]
                            )
                        write_report(args.output, report)
                path.unlink()
    if not report["results"]:
        report["configuration_error"] = (
            "no compatible workload/library/format combination"
        )
        write_report(args.output, report)
        raise SystemExit(2)
    if args.baseline:
        try:
            report["regression_checks"] = regression_checks(
                report, baseline, args.regression_margin
            )
            failed = failed or any(
                not row["passed"] for row in report["regression_checks"]
            )
        except (ValueError, KeyError, TypeError) as error:
            report["baseline_error"] = str(error)
            failed = True
        write_report(args.output, report)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
