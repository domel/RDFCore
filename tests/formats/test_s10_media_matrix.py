"""Parameterized MIME dispatch, direct plugins and RDF12 sink contracts."""
from io import BytesIO, StringIO

import pytest

from rdfcore import Dataset, Graph, Literal, TripleTerm, URIRef, plugin
from rdfcore.compare import isomorphic
from rdfcore.serializer import Serializer
from rdfcore.parser import Parser, create_input_source
from rdfcore.streaming import DatasetSink, GraphSink

FORMATS = [('text/turtle', Graph), ('application/trig', Dataset),
           ('application/n-triples', Graph), ('application/n-quads', Dataset)]


@pytest.mark.parametrize('mime,cls', FORMATS)
@pytest.mark.parametrize('version', ['1.1', '1.2-basic', '1.2'])
@pytest.mark.parametrize('empty', [False, True])
@pytest.mark.parametrize('canonical', [False, True])
def test_profile_empty_duplicate_named_and_direct_plugin_matrix(mime, cls, version, empty, canonical):
    graph = cls()
    obj = Literal('v') if version == '1.1' else Literal('v', lang='en', direction='rtl')
    if version == '1.2':
        obj = TripleTerm(URIRef('urn:a'), URIRef('urn:b'), obj)
    if not empty:
        triple = (URIRef('urn:s'), URIRef('urn:p'), obj)
        graph.add(triple).add(triple)
        if cls is Dataset:
            graph.graph(URIRef('urn:g')).add(triple).add(triple)
    format = mime+'; version='+version
    encoded = graph.serialize(format=format, encoding='utf-8', canonical=canonical)
    restored = cls().parse(data=encoded, format=format)
    assert isomorphic(graph, restored)
    output = BytesIO()
    plugin.get(format, Serializer).getClass()(graph).serialize(output, encoding='utf-8', canonical=canonical)
    assert not output.closed
    assert isomorphic(graph, cls().parse(data=output.getvalue(), format=format))
    direct = cls()
    sink = DatasetSink(direct) if cls is Dataset else GraphSink(direct)
    result = plugin.get(format, Parser).getClass()().parse(create_input_source(data=encoded), sink)
    assert result is sink
    assert isomorphic(graph, direct)


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset),
                                     ('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
@pytest.mark.parametrize('output_type', [BytesIO, StringIO])
def test_rdf12_serializers_choose_sink_protocol_before_writing(format, cls, mode, output_type):
    graph = cls()
    graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('v')))
    output = output_type()
    assert graph.serialize(output, format=format, mode=mode) is graph
    assert isomorphic(graph, cls().parse(data=output.getvalue(), format=format))
    assert not output.closed


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset),
                                     ('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
def test_typeerror_after_partial_write_is_not_retried(format, cls, mode):
    error = TypeError('sink failed after accepting data')
    class Sink:
        calls = 0
        def write(self, payload):
            self.calls += 1
            raise error
    graph = cls()
    graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('v')))
    output = Sink()
    with pytest.raises(TypeError) as caught:
        graph.serialize(output, format=format, encoding='utf-8', mode=mode)
    assert caught.value is error
    assert output.calls == 1


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
def test_stream_serializer_auto_profile_is_independent_of_statement_order(format, cls):
    graph = cls()
    graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('v')))
    graph.add((URIRef('urn:s'), URIRef('urn:q'),
               TripleTerm(URIRef('urn:a'), URIRef('urn:b'), URIRef('urn:c'))))
    encoded = graph.serialize(format=format, mode='stream')
    assert encoded.startswith('VERSION "1.2"')
    assert isomorphic(graph, cls().parse(data=encoded, format=format))


def test_custom_registry_entry_wins_over_media_parameter_dispatch(monkeypatch):
    from rdfcore.plugins.parsers.ntriples import NTParser
    from rdfcore.plugins.serializers.nt12 import NT12Serializer
    name = 'application/n-triples; version=private-test'
    monkeypatch.setitem(plugin._registry, (name, Parser), plugin.Plugin(name, Parser, implementation=NTParser))
    monkeypatch.setitem(plugin._registry, (name, Serializer), plugin.Plugin(name, Serializer, implementation=NT12Serializer))
    graph = Graph().parse(data='<urn:s> <urn:p> "v" .', format=name)
    assert isomorphic(graph, Graph().parse(data=graph.serialize(format=name), format=name))


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
def test_stream_canonical_honors_lexical_options(format, cls):
    graph = cls().add((URIRef('urn:s'), URIRef('urn:p'), Literal('v', lang='EN', direction='rtl')))
    encoded = graph.serialize(format=format, mode='stream', canonical=True)
    assert 'VERSION' not in encoded
    assert '"v"@en--rtl' in encoded
    assert isomorphic(graph, cls().parse(data=encoded, format=format))
