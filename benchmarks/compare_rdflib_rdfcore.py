"""Comparable RDFLib/RDFCore microbenchmarks.

Run from the project root, for example:
    python benchmarks/compare_rdflib_rdfcore.py --statements 10000
"""

from __future__ import annotations

import argparse
import gc
import io
import json
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rdflib
from rdflib import Graph as RDFLibGraph

import rdfcore
from rdfcore import Graph, Literal, SQLiteStore, URIRef, external_sort, parse_stream
from rdfcore.pipeline import convert


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


def measure(label, function):
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if isinstance(result, (str, bytes, bytearray)):
        result = {"type": type(result).__name__, "bytes": len(result)}
    elif isinstance(result, (int, float, bool)) or result is None:
        result = result
    else:
        result = {"type": type(result).__name__}
    return {"test": label, "seconds": elapsed, "peak_python_bytes": peak, "result": result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statements", type=int, nargs="+", default=[1000, 10000])
    args = parser.parse_args()
    rows = []
    for size in args.statements:
        for format in ("nq", "ttl", "trig"):
            payload = data(format, size)
            rows.extend((format, size, item) for item in benchmarks(payload, size, format))
    print(json.dumps({"rdflib": rdflib.__version__, "rdfcore": rdfcore.__version__, "results": rows}, indent=2))


def benchmarks(payload, size, format):
    graph_format = {"nq": "nquads", "ttl": "turtle", "trig": "trig"}[format]
    is_dataset = format in ("nq", "trig")
    rdf_graph = rdflib.Dataset() if is_dataset else RDFLibGraph()
    core_graph = rdfcore.Dataset() if is_dataset else Graph()
    rows = []
    rows.append(measure(f"rdflib.parse.{format}", lambda: len(rdf_graph.parse(data=payload, format=graph_format))))
    rows.append(measure(f"rdfcore.parse.{format}", lambda: len(core_graph.parse(data=payload, format=graph_format))))
    rows.append(measure(f"rdfcore.parse.{format}.streaming", lambda: rdfcore.count(io.BytesIO(payload), graph_format)))
    rows.append(measure(f"rdflib.serialize.{format}", lambda: rdf_graph.parse(data=payload, format=graph_format).serialize(format=graph_format)))
    rows.append(measure(f"rdfcore.serialize.{format}", lambda: core_graph.parse(data=payload, format=graph_format).serialize(format=graph_format)))
    rows.append(measure(f"rdfcore.serialize.{format}.stream", lambda: core_graph.parse(data=payload, format=graph_format).serialize(format=graph_format, mode="stream")))
    if format == "nq":
        rows.append(measure(
            "rdfcore.external_sort.unique",
            lambda: sum(1 for _ in external_sort(
                parse_stream(io.BytesIO(payload), "nquads"), memory_budget=4096, unique=True
            )),
        ))

    def sqlite_ingest():
        store = SQLiteStore(":memory:")
        graph = rdfcore.Dataset(store=store) if is_dataset else Graph(store=store)
        graph.parse(data=payload, format=graph_format)
        count = len(graph)
        store.close()
        return count

    rows.append(measure(f"rdfcore.sqlite_store.{format}.ingest", sqlite_ingest))
    for row in rows:
        row["statements"] = size
    return rows


if __name__ == "__main__":
    main()
