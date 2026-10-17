"""Comparable RDFLib/RDFCore microbenchmarks.

Run from the project root, for example:
    python benchmarks/compare_rdflib_rdfcore.py --statements 10000
"""

from __future__ import annotations

import argparse
import gc
import io
import json
import platform
from functools import partial
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rdflib
from rdflib import Graph as RDFLibGraph

import rdfcore
from rdfcore import Graph, Literal, SQLiteStore, URIRef, external_sort, parse_stream


def verify_equivalence(left, right):
    """Exact controlled-workload observables, outside timed sections.

    Fixtures deliberately have no blank nodes. This is not a general RDF
    isomorphism algorithm or a normalizer for arbitrary library differences.
    """
    def records(graph):
        def term(value):
            if value is None:
                return None
            return (type(value).__name__, str(value), getattr(value, 'language', None),
                    str(getattr(value, 'datatype', None)), getattr(value, 'direction', None))
        statements = graph.quads() if hasattr(graph, 'quads') else graph
        return {tuple(term(value) for value in statement) for statement in statements}
    assert records(left) == records(right), 'benchmark RDF data differs'


def nt_data(size):
    return "".join(
        f'<urn:s{i % (size // 10 + 1)}> <urn:p{i % 17}> "value-{i}" .\n'
        for i in range(size)
    ).encode()


def data(format, size):
    if format == "nt":
        return nt_data(size)
    if format == "nq":
        return b"".join(
            f'<urn:s{i % (size // 10 + 1)}> <urn:p{i % 17}> "value-{i}" <urn:g{i % 5}> .\n'.encode()
            for i in range(size)
        )
    if format == "ttl":
        return b"@prefix e: <urn:> .\n" + b"".join(
            f"e:s{i % (size // 10 + 1)} e:p{i % 17} \"value-{i}\" .\n".encode()
            for i in range(size)
        )
    if format == "trig":
        return b"@prefix e: <urn:> .\n" + b"".join(
            f"e:g{i % 5} {{ e:s{i % (size // 10 + 1)} e:p{i % 17} \"value-{i}\" . }}\n".encode()
            for i in range(size)
        )
    raise ValueError(format)


def _measure_once(label, function):
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = function()
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if isinstance(result, (str, bytes, bytearray)):
        result = {"type": type(result).__name__, "bytes": len(result)}
    elif isinstance(result, (int, float, bool)) or result is None:
        result = result
    else:
        result = {"type": type(result).__name__}
    return {"test": label, "seconds": elapsed, "peak_python_bytes": peak, "result": result}


def measure(label, function, *, repeats=1, warmup=0, setup=None):
    if repeats < 1 or warmup < 0:
        raise ValueError('repeats must be positive and warmup nonnegative')
    for _ in range(warmup):
        (setup() if setup else function)()
    runs = [_measure_once(label, setup() if setup else function) for _ in range(repeats)]
    return {**runs[-1], 'seconds': statistics.median(run['seconds'] for run in runs),
            'peak_python_bytes': max(run['peak_python_bytes'] for run in runs), 'runs': runs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statements", type=int, nargs="+", default=[1000, 10000])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--warmup', type=int, default=0)
    args = parser.parse_args()
    if any(size <= 0 for size in args.statements):
        parser.error('--statements must be positive')
    if args.repeats < 1 or args.warmup < 0:
        parser.error('repeats must be positive and warmup nonnegative')
    rows = []
    for size in args.statements:
        for format in ("nq", "ttl", "trig"):
            payload = data(format, size)
            rows.extend((format, size, item) for item in benchmarks(payload, size, format,
                        repeats=args.repeats, warmup=args.warmup))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
    report = json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
                         'rdfcore_revision': revision, 'worktree_dirty': dirty,
                         "rdflib": rdflib.__version__, "rdfcore": rdfcore.__version__,
                         'measurement': 'median seconds, maximum tracemalloc Python allocation peak, not RSS; correctness checked outside timings',
                         'repeats': args.repeats, 'warmup': args.warmup,
                         "results": rows}, indent=2) + '\n'
    if args.output is not None:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


def benchmarks(payload, size, format, *, repeats=1, warmup=0):
    run = partial(measure, repeats=repeats, warmup=warmup)
    graph_format = {"nq": "nquads", "ttl": "turtle", "trig": "trig"}[format]
    is_dataset = format in ("nq", "trig")
    rdf_graph = rdflib.Dataset() if is_dataset else RDFLibGraph()
    core_graph = rdfcore.Dataset() if is_dataset else Graph()
    rows = []
    def setup_parse(module):
        graph = module.Dataset() if is_dataset else module.Graph()
        return lambda: len(graph.parse(data=payload, format=graph_format))
    rows.append(run(f"rdflib.parse.{format}", None, setup=lambda: setup_parse(rdflib)))
    rows.append(run(f"rdfcore.parse.{format}", None, setup=lambda: setup_parse(rdfcore)))
    rows.append(run(f"rdfcore.parse.{format}.streaming", lambda: rdfcore.count(io.BytesIO(payload), graph_format)))
    rdf_graph.parse(data=payload, format=graph_format)
    core_graph.parse(data=payload, format=graph_format)
    assert all(row['result'] == size for row in rows)
    verify_equivalence(rdf_graph, core_graph)
    captured = []
    def serialize(graph, stream=False):
        if stream and format == 'nq':
            output = io.StringIO()
            writer = rdfcore.NQStreamingWriter(output)
            for statement in graph.quads():
                writer.add(statement)
            value = output.getvalue()
        else:
            value = graph.serialize(format=graph_format, **({'mode': 'stream'} if stream else {}))
        captured.append(value)
        return value
    rows.append(run(f"rdflib.serialize.{format}", lambda: serialize(rdf_graph)))
    rows.append(run(f"rdfcore.serialize.{format}", lambda: serialize(core_graph)))
    rows.append(run(f"rdfcore.serialize.{format}.stream", lambda: serialize(core_graph, True)))
    for value in captured:
        restored = (rdflib.Dataset() if is_dataset else RDFLibGraph()).parse(data=value, format=graph_format)
        verify_equivalence(rdf_graph, restored)
    streamed = rdfcore.Dataset() if is_dataset else Graph()
    sink = rdfcore.DatasetSink(streamed) if is_dataset else rdfcore.GraphSink(streamed)
    parse_stream(io.BytesIO(payload), graph_format, sink)
    verify_equivalence(core_graph, streamed)
    if format == "nq":
        rows.append(run(
            "rdfcore.external_sort.unique",
            lambda: sum(1 for _ in external_sort(
                parse_stream(io.BytesIO(payload), "nquads"), memory_budget=4096, unique=True
            )),
        ))
        assert rows[-1]['result'] == size
        assert set(external_sort(parse_stream(io.BytesIO(payload), 'nquads'),
                                 memory_budget=4096, unique=True)) == set(core_graph.quads())

    def sqlite_ingest(verify=False):
        store = SQLiteStore(":memory:")
        try:
            graph = rdfcore.Dataset(store=store) if is_dataset else Graph(store=store)
            graph.parse(data=payload, format=graph_format)
            if verify:
                verify_equivalence(core_graph, graph)
            return len(graph)
        finally:
            store.close()

    rows.append(run(f"rdfcore.sqlite_store.{format}.ingest", sqlite_ingest))
    assert sqlite_ingest(verify=True) == size
    for row in rows:
        row["statements"] = size
        row['correctness_verified'] = True
    return rows


if __name__ == "__main__":
    main()
