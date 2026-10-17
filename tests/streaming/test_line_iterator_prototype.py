"""Contract observations deciding whether a native adapter can replace push."""

from io import BytesIO, StringIO
from threading import Event, get_ident

import pytest
import rdflib

from benchmarks.line_iterator import _native_lines
from rdfcore import streaming
from rdfcore.exceptions import ParserError
from rdfcore.parser import InputSource, Parser
from rdfcore import plugin


@pytest.mark.parametrize('format', ['nt', 'nquads'])
@pytest.mark.parametrize('data', [b'', b'# comment\n\n',
    b'_:x <urn:p> _:x .\n_:y <urn:p> "1"^^<http://www.w3.org/2001/XMLSchema#integer> .\n',
    '<urn:s> <urn:p> "ż🙂" .\n'.encode()])
def test_native_records_match_threaded_and_reference(format, data):
    expected = list(streaming.parse_stream(BytesIO(data), format, preserve_bnode_ids=True))
    actual = list(_native_lines(BytesIO(data), format, preserve_bnode_ids=True))
    assert actual == expected
    # Independent RDFLib oracle, controlling blank-node labels via isomorphism.
    from rdfcore import Dataset
    from rdfcore.compare import isomorphic
    reference = rdflib.Dataset().parse(data=data, format=format)
    reference_dataset = Dataset().parse(data=reference.serialize(format='nquads'), format='nquads')
    core = Dataset()
    for record in actual:
        core.default_graph.add(record[:3])
    assert isomorphic(core, reference_dataset)


def test_named_and_default_graphs_match_without_flattening():
    from rdfcore import Dataset, URIRef
    from rdfcore.compare import isomorphic
    data = b'_:x <urn:p> "default" .\n_:x <urn:p> "named" <urn:g> .\n'
    reference = rdflib.Dataset().parse(data=data, format='nquads')
    expected = Dataset().parse(data=reference.serialize(format='nquads'), format='nquads')
    actual = Dataset()
    records = list(_native_lines(BytesIO(data), 'nquads'))
    assert records[0][3] is None
    assert records[1][3] == URIRef('urn:g')
    for record in records:
        graph = actual.default_graph if record[3] is None else actual.graph(record[3])
        graph.add(record[:3])
    assert isomorphic(actual, expected)


@pytest.mark.parametrize('format', ['nt', 'nquads'])
@pytest.mark.parametrize('bad', [b'invalid\n', b'\xff\n', b'<urn:s> <urn:p> "x" . bad\n'])
def test_native_errors_match_threaded(format, bad):
    errors = []
    for factory in (streaming.parse_stream, _native_lines):
        with pytest.raises(ParserError) as caught:
            list(factory(BytesIO(bad), format))
        errors.append((type(caught.value), str(caught.value)))
    assert errors[0] == errors[1]


@pytest.mark.parametrize('factory', [streaming.parse_stream, _native_lines])
def test_sources_are_lazy_and_owned_sources_close(monkeypatch, factory):
    opened = []
    handle = BytesIO(b'<urn:s> <urn:p> "x" .\n' * 3)
    def source(*args, **kwargs):
        opened.append(True)
        return InputSource(file=handle, auto_close=True)
    monkeypatch.setattr('rdfcore.parser.create_input_source', source)
    monkeypatch.setattr('benchmarks.line_iterator.create_input_source', source)
    iterator = factory('unused.nt', 'nt')
    assert not opened
    next(iterator)
    iterator.close()
    assert opened and handle.closed


def test_native_changes_producer_thread_and_read_ahead():
    main_thread = get_ident()
    class Source(StringIO):
        def __init__(self):
            super().__init__('<urn:s> <urn:p> "x" .\n' * 3)
            self.readers = []
            self.ahead = Event()
        def __next__(self):
            self.readers.append(get_ident())
            if len(self.readers) == 3:
                self.ahead.set()
            return super().__next__()
    threaded_source, native_source = Source(), Source()
    threaded = streaming.parse_stream(threaded_source, 'nt')
    native = _native_lines(native_source, 'nt')
    try:
        next(threaded)
        assert threaded_source.ahead.wait(2)
        next(native)
        assert native_source.readers == [main_thread]
        assert all(reader != main_thread for reader in threaded_source.readers)
        assert len(threaded_source.readers) >= 3
        assert not native_source.ahead.is_set()
    finally:
        threaded.close()
        native.close()


def test_replaced_plugin_is_not_silently_bypassed(monkeypatch):
    class CustomParser(Parser):
        def parse(self, source, sink, **kwargs):
            from rdfcore import URIRef
            sink.add((URIRef('urn:custom'), URIRef('urn:p'), URIRef('urn:o')))
    monkeypatch.setitem(plugin._registry, ('nt', Parser), plugin.Plugin('nt', Parser, implementation=CustomParser))
    assert str(next(streaming.parse_stream(BytesIO(), 'nt'))[0]) == 'urn:custom'
    with pytest.raises(ValueError, match='built-in'):
        next(_native_lines(BytesIO(), 'nt'))


@pytest.mark.parametrize('format', ['nt', 'nquads'])
@pytest.mark.parametrize('factory', [streaming.parse_stream, _native_lines])
def test_compressed_one_byte_input_and_caller_ownership(factory, format):
    import gzip
    from rdfcore.io import open_input
    data = '<urn:s> <urn:p> "ż🙂" .\n'.encode()
    raw = BytesIO(gzip.compress(data))
    source, _ = open_input(raw, compression='gz', buffer_size=1)
    try:
        records = list(factory(streaming.BoundedReadStream(source, chunk_size=1), format))
        assert len(records) == 1 and str(records[0][2]) == 'ż🙂'
        assert records[0][3] is None
        assert not source.closed
    finally:
        source.close()
    assert not raw.closed


def test_prototype_close_before_start_does_not_open_source(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('opened before first iteration')
    monkeypatch.setattr('benchmarks.line_iterator.create_input_source', unexpected)
    iterator = _native_lines('unused.nt', 'nt')
    iterator.close()


def test_default_mode_still_starts_a_worker(monkeypatch):
    from tests.streaming.test_iterator_lifecycle import capture_workers
    workers = capture_workers(monkeypatch)
    assert len(list(streaming.parse_stream(BytesIO(b'<urn:s> <urn:p> "x" .\n'), 'nt'))) == 1
    assert len(workers) == 1 and not workers[0].is_alive()
