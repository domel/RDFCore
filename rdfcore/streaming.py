"""Streaming contracts and Graph/Dataset adapters.

The contracts intentionally use the small ``add`` protocol already expected by
the RDFCore parsers.  They do not retain statements unless the selected
adapter points at an in-memory Graph or Dataset.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .dataset import DATASET_DEFAULT_GRAPH_ID
from .plugins.serializers.nt import _term
from .term import BNode, Literal, TripleTerm, URIRef

_NO_GRAPH = object()


@runtime_checkable
class TripleSink(Protocol):
    def add(self, triple): ...


@runtime_checkable
class QuadSink(Protocol):
    def add(self, quad): ...


class FilterSink:
    """Forward statements for which ``predicate`` returns true."""

    def __init__(self, sink, predicate):
        self.sink = sink
        self.predicate = predicate

    def add(self, statement):
        if self.predicate(statement):
            self.sink.add(statement)


class MapSink:
    """Apply a bounded per-statement transform before forwarding."""

    def __init__(self, sink, mapper):
        self.sink = sink
        self.mapper = mapper

    def add(self, statement):
        mapped = self.mapper(statement)
        if mapped is not None:
            self.sink.add(mapped)


class GraphSink:
    """Adapt a Graph-like object to a triple sink."""

    def __init__(self, graph):
        self.graph = graph

    def add(self, statement):
        if len(statement) != 3:
            raise ValueError("GraphSink accepts triples only")
        self.graph.add(tuple(statement))


class DatasetSink:
    """Adapt a Dataset-like object to a quad sink.

    A three-item statement is written to the dataset's default graph.  A
    four-item statement uses its graph identifier and preserves named-graph
    boundaries.
    """

    def __init__(self, dataset):
        self.dataset = dataset

    def add(self, statement):
        if len(statement) == 3:
            self.dataset.add(tuple(statement))
        elif len(statement) == 4:
            self.dataset.add(tuple(statement))
        else:
            raise ValueError("DatasetSink accepts triples or quads")


class BoundedReadStream:
    """Reader wrapper that caps each explicit read to ``chunk_size`` bytes."""

    def __init__(self, stream, chunk_size=8192):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.stream = stream
        self.chunk_size = chunk_size
        self._buffer = stream.read(0)

    def _empty(self):
        return self._buffer[:0]

    def _read_chunk(self, size):
        return self.stream.read(min(size, self.chunk_size))

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.chunk_size
        size = min(size, self.chunk_size)
        prefix, self._buffer = self._buffer[:size], self._buffer[size:]
        if len(prefix) == size:
            return prefix
        return prefix + self._read_chunk(size - len(prefix))

    def readline(self, size=-1):
        parts = []
        remaining = size
        while remaining != 0:
            newline = self._buffer.find(b"\n" if isinstance(self._buffer, bytes) else "\n")
            take = len(self._buffer) if newline < 0 else newline + 1
            if remaining > 0:
                take = min(take, remaining)
            if take:
                parts.append(self._buffer[:take])
                self._buffer = self._buffer[take:]
                if newline >= 0 or (remaining > 0 and take == remaining):
                    break
                if remaining > 0:
                    remaining -= take
            chunk = self._read_chunk(self.chunk_size)
            if not chunk:
                break
            self._buffer += chunk
        return self._empty().join(parts)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if line == "" or line == b"":
            raise StopIteration
        return line

    def __getattr__(self, name):
        return getattr(self.stream, name)


class NTStreamingWriter:
    """Write triples immediately to a text or binary file-like object."""

    def __init__(self, stream, *, encoding="utf-8", canonical=False):
        self.stream = stream
        self.encoding = encoding
        self.canonical = canonical

    def add(self, triple):
        if len(triple) != 3:
            raise ValueError("NTStreamingWriter accepts triples only")
        subject, predicate, obj = triple
        line = f"{_term(subject, canonical=self.canonical)} {_term(predicate, canonical=self.canonical)} {_term(obj, canonical=self.canonical)} .\n"
        try:
            self.stream.write(line)
        except TypeError:
            self.stream.write(line.encode(self.encoding))

    def close(self):
        return None


class NQStreamingWriter:
    """Write N-Quads statements immediately, including the default graph."""

    def __init__(self, stream, *, encoding="utf-8", canonical=False):
        self.stream = stream
        self.encoding = encoding
        self.canonical = canonical

    def add(self, statement):
        if len(statement) == 3:
            subject, predicate, obj = statement
            graph = None
        elif len(statement) == 4:
            subject, predicate, obj, graph = statement
        else:
            raise ValueError("NQStreamingWriter accepts triples or quads")
        parts = [_term(subject, canonical=self.canonical), _term(predicate, canonical=self.canonical), _term(obj, canonical=self.canonical)]
        if graph is not None and graph != DATASET_DEFAULT_GRAPH_ID:
            parts.append(_term(graph, canonical=self.canonical))
        line = " ".join(parts) + " .\n"
        try:
            self.stream.write(line)
        except TypeError:
            self.stream.write(line.encode(self.encoding))

    def close(self):
        return None


class TurtleStreamingWriter:
    """Write Turtle statements immediately, without prefix/global sorting."""

    def __init__(self, stream, *, encoding="utf-8", rdf_version="auto"):
        if rdf_version not in ("auto", "1.1", "1.2-basic", "1.2"):
            raise ValueError(f"unsupported rdf_version {rdf_version!r}")
        self.stream = stream
        self.encoding = encoding
        self.rdf_version = rdf_version
        self._version_written = False
        self._emitted_version = "1.1"
        self._started = False
        if rdf_version in ("1.2-basic", "1.2"):
            self._write(f'VERSION "{rdf_version}"\n')
            self._version_written = True
            self._emitted_version = rdf_version

    def add(self, triple):
        if len(triple) != 3:
            raise ValueError("TurtleStreamingWriter accepts triples only")
        subject, predicate, obj = triple
        required = "1.2" if isinstance(obj, TripleTerm) else "1.2-basic" if isinstance(obj, Literal) and obj.direction else "1.1"
        if self.rdf_version == "1.1" and required != "1.1":
            raise ValueError(f"RDF {required} term requires an RDF 1.2 streaming writer")
        if self.rdf_version == "1.2-basic" and required == "1.2":
            raise ValueError("RDF 1.2 triple terms require rdf_version='1.2'")
        if required != "1.1" and not self._version_written:
            if self._started:
                raise ValueError("cannot upgrade a started Turtle stream from RDF 1.1 to RDF 1.2")
            version = self.rdf_version if self.rdf_version != "auto" else required
            self._write(f'VERSION "{version}"\n')
            self._version_written = True
            self._emitted_version = version
        if self._emitted_version == "1.2-basic" and required == "1.2":
            raise ValueError("cannot upgrade a started Turtle stream from RDF 1.2-basic to RDF 1.2")
        self._write(f"{_turtle_term(subject)} {_turtle_term(predicate)} {_turtle_term(obj)} .\n")
        self._started = True

    def _write(self, text):
        try:
            self.stream.write(text)
        except TypeError:
            self.stream.write(text.encode(self.encoding))

    def close(self):
        return None


def _turtle_term(term):
    if isinstance(term, URIRef):
        return term.n3()
    if isinstance(term, BNode):
        return term.n3()
    if isinstance(term, Literal):
        return term.n3()
    if isinstance(term, TripleTerm):
        return "<<( " + " ".join(_turtle_term(item) for item in term) + " )>>"
    raise TypeError(f"unsupported RDF term: {term!r}")


class TriGStreamingWriter:
    """Write quads as contiguous TriG blocks without grouping the dataset."""

    def __init__(self, stream, *, encoding="utf-8", rdf_version="auto"):
        if rdf_version not in ("auto", "1.1", "1.2-basic", "1.2"):
            raise ValueError(f"unsupported rdf_version {rdf_version!r}")
        self.stream = stream
        self.encoding = encoding
        self.rdf_version = rdf_version
        self._graph = _NO_GRAPH
        self._closed = False
        self._emitted_version = rdf_version if rdf_version != "auto" else "1.1"
        if rdf_version in ("1.2-basic", "1.2"):
            self._write(f'VERSION "{rdf_version}"\n')

    def add(self, statement):
        if self._closed:
            raise ValueError("cannot add statements after TriGStreamingWriter.close()")
        if len(statement) == 3:
            subject, predicate, obj = statement
            graph = None
        elif len(statement) == 4:
            subject, predicate, obj, graph = statement
        else:
            raise ValueError("TriGStreamingWriter accepts triples or quads")
        required = "1.2" if isinstance(obj, TripleTerm) else "1.2-basic" if isinstance(obj, Literal) and obj.direction else "1.1"
        if self.rdf_version == "1.1" and required != "1.1":
            raise ValueError(f"RDF {required} term requires an RDF 1.2 streaming writer")
        if self.rdf_version == "1.2-basic" and required == "1.2":
            raise ValueError("RDF 1.2 triple terms require rdf_version='1.2'")
        if self.rdf_version == "auto" and required != "1.1" and self._emitted_version == "1.1":
            if self._graph is not _NO_GRAPH:
                raise ValueError("cannot upgrade a started TriG stream from RDF 1.1 to RDF 1.2")
            self._write(f'VERSION "{required}"\n')
            self._emitted_version = required
        if self._emitted_version == "1.2-basic" and required == "1.2":
            raise ValueError("cannot upgrade a started TriG stream from RDF 1.2-basic to RDF 1.2")
        graph = None if graph == DATASET_DEFAULT_GRAPH_ID else graph
        if graph != self._graph:
            self._close_graph()
            if graph is None:
                self._write("{\n")
            else:
                self._write(f"{_turtle_term(graph)} {{\n")
            self._graph = graph
        self._write(f"  {_turtle_term(subject)} {_turtle_term(predicate)} {_turtle_term(obj)} .\n")

    def _close_graph(self):
        if self._graph is not _NO_GRAPH:
            self._write("}\n")

    def _write(self, text):
        try:
            self.stream.write(text)
        except TypeError:
            self.stream.write(text.encode(self.encoding))

    def close(self):
        if not self._closed and self._graph is not _NO_GRAPH:
            self._write("}\n")
        self._closed = True


def parse_stream(source=None, format=None, sink=None, **kwargs):
    """Parse *source* directly into *sink* and return the sink.

    This function deliberately bypasses ``Graph.parse``/``Dataset.parse``;
    parser statements are delivered directly to the supplied backend.
    """
    from .parser import create_input_source
    from .plugin import get as get_plugin
    from .parser import Parser

    if format is None:
        raise ValueError("parse_stream() requires a format")

    def push(target):
        input_source = create_input_source(source, format=format, **kwargs)
        parser_class = get_plugin(format, Parser).getClass()
        try:
            parser_class().parse(input_source, target, **kwargs)
        finally:
            input_source.close()
        return target

    if sink is not None:
        return push(sink)

    def statements():
        # A bounded queue preserves streaming behavior while adapting parsers
        # with a push API to the public iterator API.
        from queue import Full, Queue
        from threading import Event, Thread

        end = object()
        queue = Queue(maxsize=1)
        stopped = Event()

        class StopStreaming(Exception):
            pass

        class QueueSink:
            def add(self, statement):
                if len(statement) == 3:
                    statement = (*statement, None)
                while not stopped.is_set():
                    try:
                        queue.put(statement, timeout=0.05)
                        return
                    except Full:
                        pass
                raise StopStreaming

        def run():
            try:
                push(QueueSink())
            except StopStreaming:
                pass
            except BaseException as error:
                if not stopped.is_set():
                    queue.put(error)
            finally:
                if not stopped.is_set():
                    queue.put(end)

        Thread(target=run, daemon=True).start()
        try:
            while True:
                item = queue.get()
                if item is end:
                    return
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            stopped.set()

    return statements()
