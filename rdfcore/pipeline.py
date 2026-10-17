"""Small streaming pipeline entry points."""

from __future__ import annotations

from contextlib import ExitStack

from .io import open_input, open_output
from .streaming import NQStreamingWriter, NTStreamingWriter, parse_stream
from .rdf_version import required_rdf_version


class _RDF12Writer:
    """Emit individual lines using the existing RDF 1.2 term formatter."""

    def __init__(self, stream, *, dataset, canonical=False):
        self.stream, self.dataset, self.canonical = stream, dataset, canonical
        if not canonical:
            self._write('VERSION "1.2"\n')

    def _write(self, text):
        try:
            self.stream.write(text)
        except TypeError:
            self.stream.write(text.encode('utf-8'))

    def add(self, statement):
        from .plugins.serializers.nt12 import _term
        parts = [_term(term, canonical=self.canonical) for term in statement[:3]]
        if self.dataset and len(statement) == 4 and statement[3] is not None:
            parts.append(_term(statement[3], canonical=self.canonical))
        self._write(' '.join(parts) + ' .\n')

    def close(self):
        pass


_FORMATS = {
    **{alias: ('graph', '1.1') for alias in ('nt', 'nt11', 'ntriples', 'application/n-triples')},
    **{alias: ('dataset', '1.1') for alias in ('nquads', 'application/n-quads')},
    'nt12': ('graph', '1.2'), 'nq12': ('dataset', '1.2'),
}


def _close_stream(stream, owned, *, output=False):
    import bz2
    import gzip
    import lzma
    raw = getattr(stream, 'fileobj', getattr(stream, '_fp', getattr(stream, 'stream', None)))
    try:
        if owned or isinstance(stream, (gzip.GzipFile, bz2.BZ2File, lzma.LZMAFile)):
            stream.close()
        elif output:
            stream.flush()
    finally:
        if owned and raw is not None and raw is not stream:
            raw.close()


def _scan(source, format, *, operation, **kwargs):
    from .io import open_input

    buffer_size = kwargs.pop("buffer_size", 64 * 1024)
    compression = kwargs.pop("input_compression", None)
    stream, owned = open_input(source, compression=compression, buffer_size=buffer_size)
    count = 0

    class Sink:
        def add(self, statement):
            nonlocal count
            count += 1

    try:
        parse_stream(stream, format, Sink(), **kwargs)
    finally:
        if owned:
            stream.close()
    return count if operation == "count" else True


def count(source, format, **kwargs):
    """Count streamed RDF statements without materializing a graph."""
    return _scan(source, format, operation="count", **kwargs)


def validate(source, format, **kwargs):
    """Parse the complete input and return true if its syntax is valid."""
    return _scan(source, format, operation="validate", **kwargs)


def convert(source, destination=None, input_format=None, output_format=None, *, sink=None, **kwargs):
    """Feed a parser into a caller-provided streaming sink.

    Supported paths are direct N-Triples and N-Quads pipelines.  No Graph or
    Dataset is created for these conversions.
    """
    # Compatibility with the temporary S34 call shape:
    # convert(source, input_format, output_format, sink=...).
    if output_format is None and input_format is not None and isinstance(destination, str):
        destination, input_format, output_format = None, destination, input_format
    if not isinstance(input_format, str) or not isinstance(output_format, str):
        raise TypeError("input_format and output_format must be strings")
    if input_format not in _FORMATS or output_format not in _FORMATS:
        raise NotImplementedError("S36 streaming conversion supports nt/nquads paths only")
    buffer_size = kwargs.pop("buffer_size", 64 * 1024)
    input_compression = kwargs.pop("input_compression", None)
    output_compression = kwargs.pop("output_compression", None)
    with ExitStack() as cleanup:
        if sink is None:
            if destination is None:
                raise ValueError("convert() requires destination or sink")
            destination_stream, output_owned = open_output(
                destination, compression=output_compression, buffer_size=buffer_size)
            cleanup.callback(_close_stream, destination_stream, output_owned, output=True)
            family, version = _FORMATS[output_format]
            canonical = kwargs.pop('canonical', False)
            if version == '1.2':
                sink = _RDF12Writer(destination_stream, dataset=family == 'dataset', canonical=canonical)
            else:
                factory = NTStreamingWriter if family == 'graph' else NQStreamingWriter
                options = {'default_graph_id': None} if family == 'dataset' else {}
                sink = factory(destination_stream, canonical=canonical, **options)
        try:
            input_stream, input_owned = open_input(source, compression=input_compression, buffer_size=buffer_size)
        except BaseException:
            if hasattr(sink, 'close'):
                sink.close()
            raise
        cleanup.callback(_close_stream, input_stream, input_owned)
        if hasattr(sink, 'close'):
            cleanup.callback(sink.close)
        return _convert_stream(input_stream, input_format, output_format, sink, kwargs)


def _convert_stream(source, input_format, output_format, sink, kwargs):
    project = _FORMATS[input_format][0] == 'dataset' and _FORMATS[output_format][0] == 'graph'
    version = _FORMATS[output_format][1]
    policy = None
    if project:
        policy = kwargs.pop("dataset_policy", "strict")
        if policy not in ("strict", "default", "union"):
            raise ValueError("dataset_policy must be 'strict', 'default', or 'union'")

    class GraphFormatSink:
        def add(self, statement):
            required = required_rdf_version((statement,))
            if version == '1.1' and required != '1.1':
                raise ValueError(f'RDF {required} data cannot be converted to RDF 1.1')
            if project:
                if len(statement) == 4:
                    if statement[3] is not None and policy == "strict":
                        raise ValueError("named graph cannot be written to an N-Triples stream")
                    if statement[3] is not None and policy == "default":
                        return
                    statement = statement[:3]
            sink.add(statement)

    adapter = GraphFormatSink()
    parse_stream(source, input_format, adapter, **kwargs)
    return adapter if project else sink
