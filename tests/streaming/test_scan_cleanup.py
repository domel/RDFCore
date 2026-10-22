"""Count/validate must close owned layers without relying on finalizers."""
import bz2
import gzip
import lzma
from io import BytesIO

import pytest

from rdfcore import io, pipeline
from rdfcore.exceptions import ParserError


@pytest.mark.parametrize('operation', [pipeline.count, pipeline.validate])
@pytest.mark.parametrize('compression', [None, 'gz', 'bz2', 'xz'])
@pytest.mark.parametrize('owned', [False, True])
@pytest.mark.parametrize('valid', [False, True])
def test_scan_closes_all_owned_layers_and_keeps_caller_input_open(
        monkeypatch, operation, compression, owned, valid):
    data = b'<urn:s> <urn:p> "v" .\n' if valid else b'not RDF\n'
    if compression:
        data = {'gz': gzip, 'bz2': bz2, 'xz': lzma}[compression].compress(data)
    raw = BytesIO(data)
    stream, _ = io.open_input(raw, compression=compression, buffer_size=7)
    # Retain both objects to make explicit close observable independently
    # of garbage collection, including when an exception retains its frame.
    monkeypatch.setattr(io, 'open_input', lambda *a, **kw: (stream, owned))
    try:
        if valid:
            result = operation(raw, 'nt')
            assert result == (1 if operation is pipeline.count else True)
            assert type(result) is (int if operation is pipeline.count else bool)
        else:
            with pytest.raises(ParserError):
                operation(raw, 'nt')
        assert raw.closed is owned
        if compression:
            assert stream.closed
    finally:
        stream.close()
        raw.close()


def test_owned_input_closes_even_when_parser_raises_baseexception(monkeypatch):
    raw = BytesIO(gzip.compress(b''))
    stream, _ = io.open_input(raw, compression='gz')
    monkeypatch.setattr(io, 'open_input', lambda *a, **kw: (stream, True))
    def stop(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(pipeline, 'parse_stream', stop)
    try:
        with pytest.raises(KeyboardInterrupt):
            pipeline.count(raw, 'nt')
        assert stream.closed and raw.closed
    finally:
        stream.close()
        raw.close()
