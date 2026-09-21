"""Small streaming pipeline entry points."""

from __future__ import annotations

from .io import BoundedWriteStream, open_input, open_output
from .streaming import NQStreamingWriter, NTStreamingWriter, parse_stream


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
    supported = {("nt", "nt"), ("nt", "nquads"), ("nquads", "nquads"), ("nquads", "nt")}
    if (input_format, output_format) not in supported:
        raise NotImplementedError("S36 streaming conversion supports nt/nquads paths only")
    buffer_size = kwargs.pop("buffer_size", 64 * 1024)
    input_compression = kwargs.pop("input_compression", None)
    output_compression = kwargs.pop("output_compression", None)
    output_owned = False
    destination_stream = None
    if sink is None:
        if destination is None:
            raise ValueError("convert() requires destination or sink")
        destination_stream, output_owned = open_output(
            destination, compression=output_compression, buffer_size=buffer_size
        )
        if output_format == "nt":
            sink = NTStreamingWriter(destination_stream, canonical=kwargs.pop("canonical", False))
        elif output_format == "nquads":
            sink = NQStreamingWriter(destination_stream, canonical=kwargs.pop("canonical", False))
    input_stream, input_owned = open_input(
        source, compression=input_compression, buffer_size=buffer_size
    )
    try:
        return _convert_stream(input_stream, input_format, output_format, sink, kwargs)
    finally:
        if hasattr(sink, "close"):
            sink.close()
        if input_owned or input_stream.__class__.__name__ in ("GzipFile", "BZ2File", "LZMAFile"):
            input_stream.close()
        if input_owned:
            raw_input = getattr(input_stream, "fileobj", getattr(input_stream, "stream", None))
            if raw_input is not None and raw_input is not input_stream:
                raw_input.close()
        if destination_stream is not None:
            if output_owned or not isinstance(destination_stream, BoundedWriteStream):
                destination_stream.close()
            else:
                destination_stream.flush()
        if destination_stream is not None and output_owned:
            raw_output = getattr(destination_stream, "fileobj", getattr(destination_stream, "stream", None))
            if raw_output is not None and raw_output is not destination_stream:
                raw_output.close()


def _convert_stream(source, input_format, output_format, sink, kwargs):
    if input_format == "nquads" and output_format == "nt":
        policy = kwargs.pop("dataset_policy", "strict")
        if policy not in ("strict", "default", "union"):
            raise ValueError("dataset_policy must be 'strict', 'default', or 'union'")

        class GraphFormatSink:
            def add(self, statement):
                if len(statement) == 4:
                    if statement[3] is not None and policy == "strict":
                        raise ValueError("named graph cannot be written to an N-Triples stream")
                    if statement[3] is not None and policy == "default":
                        return
                    statement = statement[:3]
                sink.add(statement)

        return parse_stream(source, input_format, GraphFormatSink(), **kwargs)
    return parse_stream(source, input_format, sink, **kwargs)
