"""Published October 2026 syntax media types; XML dispatch is an extension."""
from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, Literal, TripleTerm, URIRef, convert, parse_stream, plugin
from rdfcore.compare import isomorphic
from rdfcore.parser import Parser
from rdfcore.serializer import Serializer

FORMATS = [('text/turtle', 'turtle12', Graph), ('application/trig', 'trig12', Dataset),
           ('application/n-triples', 'nt12', Graph), ('application/n-quads', 'nq12', Dataset),
           ('application/rdf+xml', 'xml12', Graph)]


def make_graph(cls, triple_term=False):
    graph = cls()
    obj = Literal('text', lang='en', direction='rtl')
    if triple_term:
        obj = TripleTerm(URIRef('urn:a'), URIRef('urn:b'), obj)
    graph.add((URIRef('urn:s'), URIRef('urn:p'), obj))
    return graph


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
@pytest.mark.parametrize('spelling', ['; version=1.2', ';VERSION="1.2"', ' ; charset=utf-8; version="1.2"; profile="https://e/p;a https://e/q"'])
def test_mime_version_round_trip(mime, alias, cls, spelling):
    format = mime.upper() + spelling
    graph = make_graph(cls, True)
    encoded = graph.serialize(format=format)
    assert encoded == graph.serialize(format=alias, rdf_version='1.2')
    restored = cls().parse(data=encoded, format=format)
    assert isomorphic(graph, restored)
    rows = list(parse_stream(BytesIO(encoded.encode()), format))
    assert len(rows) == 1 and isinstance(rows[0][2], TripleTerm)


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
@pytest.mark.parametrize('kind', [Parser, Serializer])
def test_plugin_lookup_honors_version(mime, alias, cls, kind):
    assert issubclass(plugin.get(mime + '; version=1.2', kind).getClass(), plugin.get(alias, kind).getClass())


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
def test_basic_profile_accepts_direction_but_rejects_triple_terms(mime, alias, cls):
    format = mime + '; version=1.2-basic'
    graph = make_graph(cls)
    encoded = graph.serialize(format=format)
    assert '1.2-basic' in encoded
    assert isomorphic(graph, cls().parse(data=encoded, format=format))
    full = make_graph(cls, True)
    with pytest.raises(ValueError):
        full.serialize(format=format)
    full_data = full.serialize(format=alias, rdf_version='1.2')
    with pytest.raises(Exception):
        cls().parse(data=full_data, format=format)


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
def test_mime_profile_conflict_precedes_file_output(mime, alias, cls, tmp_path):
    path = tmp_path / 'output.rdf'
    path.write_bytes(b'keep')
    with pytest.raises(ValueError, match='conflict'):
        cls().serialize(path, format=mime + '; version=1.2', rdf_version='1.1')
    assert path.read_bytes() == b'keep'


@pytest.mark.parametrize('suffix', ['version=auto', 'version=2.0', 'version=', 'version', 'version="1.2',
                                  'version=1.2;VERSION=1.1', 'version=1.2\r\nX: y'])
def test_invalid_media_parameters_are_not_silently_ignored(suffix):
    with pytest.raises(ValueError):
        Graph().serialize(format='text/turtle; ' + suffix)


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
def test_direct_serializer_plugin_receives_mime_profile(mime, alias, cls):
    output = BytesIO()
    serializer = plugin.get(mime + '; version=1.2-basic', Serializer).getClass()(cls())
    serializer.serialize(output, encoding='utf-8')
    assert b'1.2-basic' in output.getvalue()
    with pytest.raises(ValueError, match='conflict'):
        serializer.serialize(BytesIO(), rdf_version='1.2')


def test_xml_mime_version_does_not_replace_required_document_announcement():
    data = make_graph(Graph, True).serialize(format='xml12')
    data = data.replace(' rdf:version="1.2"', '')
    with pytest.raises(Exception):
        Graph().parse(data=data, format='application/rdf+xml; version=1.2')


@pytest.mark.parametrize('source', ['application/n-triples', 'application/n-quads'])
@pytest.mark.parametrize('target', ['application/n-triples', 'application/n-quads'])
def test_convert_parameterized_line_formats(source, target):
    data = b'<urn:s> <urn:p> "text"@en--rtl .\n'
    output = BytesIO()
    convert(BytesIO(data), output, input_format=source + '; version=1.2',
            output_format=target + '; version=1.2-basic')
    assert output.getvalue().startswith(b'VERSION "1.2-basic"\n')
    assert len(list(parse_stream(BytesIO(output.getvalue()), target + '; version=1.2-basic'))) == 1


def test_convert_rejects_full_terms_for_basic_output():
    data = b'<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .\n'
    with pytest.raises(Exception):
        convert(BytesIO(data), BytesIO(), input_format='application/n-triples; version=1.2',
                output_format='application/n-triples; version=1.2-basic')


def test_http_versioned_content_type_is_used_only_without_explicit_format(monkeypatch):
    from rdfcore import parser
    data = make_graph(Graph, True).serialize(format='nt12', rdf_version='1.2').encode()
    def response(*args, **kwargs):
        stream = BytesIO(data)
        stream.headers = {'Content-Type': 'application/n-triples; version=1.2'}
        return stream
    monkeypatch.setattr(parser, 'urlopen', response)
    graph = Graph().parse('https://example.org/data')
    assert isinstance(next(iter(graph))[2], TripleTerm)
    with pytest.raises(Exception):
        Graph().parse('https://example.org/data', format='nt')


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
def test_w3c_runner_uses_parameterized_parser(tmp_path, mime, alias, cls):
    from tests.w3c.runner import _parse
    path = tmp_path / 'input.rdf'
    path.write_text(make_graph(cls, True).serialize(format=alias, rdf_version='1.2'))
    assert isomorphic(_parse(path, mime + '; version=1.2'), _parse(path, alias))


@pytest.mark.parametrize('mime,alias,cls', FORMATS)
def test_direct_parser_rejects_full_terms_in_basic_profile(mime, alias, cls):
    from rdfcore.parser import create_input_source
    from rdfcore.streaming import GraphSink, DatasetSink
    data = make_graph(cls, True).serialize(format=alias, rdf_version='1.2')
    sink = DatasetSink(cls()) if cls is Dataset else GraphSink(cls())
    parser = plugin.get(mime + '; version=1.2-basic', Parser).getClass()()
    with pytest.raises(ValueError):
        parser.parse(create_input_source(data=data), sink, rdf_version='1.2')
    with pytest.raises(Exception):
        parser.parse(create_input_source(data=data), sink)
