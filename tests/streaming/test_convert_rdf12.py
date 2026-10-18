"""Line conversion: NT WD 2026-10-07 and NQ WD 2026-10-10."""

from io import BytesIO

import pytest

from rdfcore import Dataset, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.pipeline import convert
from rdfcore.exceptions import ParserError


DATA = b'VERSION "1.2"\n_:s <urn:p> <<( _:s <urn:q> "text"@en--rtl )>> .\n'


@pytest.mark.parametrize('source', ['nt12', 'nq12'])
@pytest.mark.parametrize('target', ['nt12', 'nq12'])
@pytest.mark.parametrize('canonical', [False, True])
def test_rdf12_roundtrip(source, target, canonical):
    output = BytesIO()
    convert(BytesIO(DATA), output, input_format=source, output_format=target, canonical=canonical)
    actual = Dataset().parse(data=output.getvalue(), format=target)
    expected = Dataset().parse(data=DATA, format=source)
    assert isomorphic(actual, expected)
    assert isinstance(next(actual.quads())[2], TripleTerm)
    assert output.getvalue().startswith(b'VERSION "1.2"\n') is (not canonical)


@pytest.mark.parametrize('policy,expected', [('strict', None), ('default', 1), ('union', 2)])
def test_dataset_policy_applies_to_rdf12(policy, expected):
    data = b'VERSION "1.2"\n<urn:s> <urn:p> "default" .\n<urn:s> <urn:p> "named" <urn:g> .\n'
    output = BytesIO()
    if expected is None:
        with pytest.raises(ParserError, match='named graph'):
            convert(BytesIO(data), output, input_format='nq12', output_format='nt12', dataset_policy=policy)
    else:
        convert(BytesIO(data), output, input_format='nq12', output_format='nt12', dataset_policy=policy)
        assert len(Dataset().parse(data=output.getvalue(), format='nt12').default_graph) == expected


@pytest.mark.parametrize('target', ['nt', 'nquads'])
@pytest.mark.parametrize('custom', [False, True])
def test_rdf12_to_rdf11_never_silently_downgrades(target, custom):
    output, received = BytesIO(), []
    class Sink:
        def add(self, statement):
            received.append(statement)
    with pytest.raises(ParserError, match='RDF 1.2') as caught:
        convert(BytesIO(DATA), None if custom else output, input_format='nt12', output_format=target,
                sink=Sink() if custom else None)
    assert isinstance(caught.value.__cause__, ValueError)
    assert not received and output.getvalue() == b''


@pytest.mark.parametrize('source', ['nt', 'nt11', 'ntriples', 'application/n-triples', 'nquads', 'application/n-quads'])
@pytest.mark.parametrize('target', ['nt12', 'nq12'])
def test_legacy_aliases_upgrade_without_changing_input(source, target):
    output = BytesIO()
    data = b'<urn:s> <urn:p> "plain" .\n'
    convert(BytesIO(data), output, input_format=source, output_format=target)
    assert len(Dataset().parse(data=output.getvalue(), format=target).default_graph) == 1


def test_rdf12_named_graphs_are_preserved():
    data = DATA.replace(b' )>> .', b' )>> <urn:g> .')
    output = BytesIO()
    convert(BytesIO(data), output, input_format='nq12', output_format='nq12')
    parsed = Dataset().parse(data=output.getvalue(), format='nq12')
    assert next(parsed.quads())[3] == URIRef('urn:g')


@pytest.mark.parametrize('source,target', [('nt12','nt12'), ('nq12','nt12'), ('nt12','nq12'), ('nq12','nq12')])
def test_empty_rdf12_input_and_repeated_calls(source, target):
    for _ in range(2):
        output = BytesIO()
        convert(BytesIO(), output, input_format=source, output_format=target)
        assert len(Dataset().parse(data=output.getvalue(), format=target)) == 0


@pytest.mark.parametrize('compression', ['gz', 'bz2', 'xz'])
def test_compressed_conversion_preserves_caller_streams(compression):
    import gzip, bz2, lzma
    codec = {'gz': gzip, 'bz2': bz2, 'xz': lzma}[compression]
    source, output = BytesIO(codec.compress(DATA)), BytesIO()
    convert(source, output, input_format='nt12', output_format='nq12',
            input_compression=compression, output_compression=compression, buffer_size=1)
    assert not source.closed and not output.closed
    assert len(Dataset().parse(data=codec.decompress(output.getvalue()), format='nq12').default_graph) == 1


def test_open_failure_and_sink_close_failure_release_owned_streams(monkeypatch):
    from rdfcore import pipeline
    output = BytesIO()
    def forbidden(*args, **kwargs):
        raise AssertionError('output opened before missing input was detected')
    monkeypatch.setattr(pipeline, 'open_output', forbidden)
    with pytest.raises(FileNotFoundError):
        convert('/path/which/does/not/exist.nt', 'out', input_format='nt12', output_format='nq12')
    assert not output.closed
    source = BytesIO(DATA)
    monkeypatch.setattr(pipeline, 'open_input', lambda *args, **kwargs: (source, True))
    class Sink:
        def add(self, statement):
            pass
        def close(self):
            raise RuntimeError('close failed')
    with pytest.raises(RuntimeError, match='close failed'):
        convert(source, input_format='nt12', output_format='nq12', sink=Sink())
    assert source.closed


def test_conversion_does_not_construct_graphs(monkeypatch):
    import rdfcore.graph
    def forbidden(*args, **kwargs):
        raise AssertionError('conversion materialized a graph')
    monkeypatch.setattr(rdfcore.graph.Graph, '__init__', forbidden)
    output = BytesIO()
    convert(BytesIO(DATA), output, input_format='nt12', output_format='nq12')
    assert b'<<(' in output.getvalue()


def test_partial_output_on_invalid_input_is_explicit():
    output = BytesIO()
    with pytest.raises(ParserError):
        convert(BytesIO(DATA + b'invalid\n'), output, input_format='nt12', output_format='nt12')
    assert b'<<(' in output.getvalue()


@pytest.mark.parametrize('format', ['nquads', 'nq12'])
def test_conversion_preserves_a_named_graph_with_the_dataset_sentinel_iri(format):
    from rdfcore import parse_stream
    data = b'<urn:s> <urn:p> "x" <urn:x-rdflib:default> .\n'
    output = BytesIO()
    convert(BytesIO(data), output, input_format=format, output_format=format)
    class Sink:
        def __init__(self): self.rows = []
        def add(self, row): self.rows.append(row)
    before, after = Sink(), Sink()
    parse_stream(BytesIO(data), format, before)
    parse_stream(BytesIO(output.getvalue()), format, after)
    assert before.rows == after.rows
