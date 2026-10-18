"""RDFLib 7.6.0 XML11 binary stream and encoding-attribute contracts."""
from io import BytesIO, StringIO
from xml.etree import ElementTree

import pytest
import rdflib
import rdfcore
from rdflib.plugins.serializers.rdfxml import XMLSerializer as ReferenceSerializer
from rdfcore.plugins.serializers.rdfxml import XMLSerializer


def graph(module):
    return module.Graph().add((module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('é😀')))


def test_xml11_requires_binary_caller_stream_like_reference():
    for module in (rdflib, rdfcore):
        stream = StringIO()
        with pytest.raises(TypeError):
            graph(module).serialize(stream, format='xml')
        assert not stream.closed


def test_xml11_does_not_retry_sink_typeerror_as_text():
    class BrokenSink:
        calls = 0
        def write(self, data):
            self.calls += 1
            raise TypeError('sink failure')
    for module in (rdflib, rdfcore):
        sink = BrokenSink()
        with pytest.raises(TypeError, match='sink failure'):
            graph(module).serialize(sink, format='xml')
        assert sink.calls == 1


def test_xml11_custom_encoding_attribute_uses_reference_replacement_policy():
    values = []
    for module, cls in ((rdflib, ReferenceSerializer), (rdfcore, XMLSerializer)):
        serializer = cls(graph(module))
        serializer.encoding = 'ascii'
        output = BytesIO()
        assert serializer.serialize(output, encoding='utf-16') is None
        assert output.getvalue().startswith(b'<?xml version="1.0" encoding="ascii"?>')
        values.append(ElementTree.fromstring(output.getvalue()).find('.//{urn:}p').text)
    assert values == ['??', '??']


@pytest.mark.parametrize('encoding', [None, 'utf-16', 'ascii'])
def test_xml11_file_destination_remains_binary_without_encoding_argument(tmp_path, encoding):
    for module in (rdflib, rdfcore):
        path = tmp_path / (module.__name__+'.rdf')
        value = graph(module)
        assert value.serialize(path, format='xml', encoding=encoding) is value
        output = path.read_bytes()
        assert output.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
        assert ElementTree.fromstring(output).find('.//{urn:}p').text == 'é😀'


@pytest.mark.parametrize('base', [None, '', 'https://example.org/override/'])
def test_direct_xml11_serializer_uses_graph_base_when_argument_is_none(base):
    observations = []
    for module, cls in ((rdflib, ReferenceSerializer), (rdfcore, XMLSerializer)):
        value = graph(module)
        value.base = 'https://example.org/graph/'
        output = BytesIO()
        assert cls(value).serialize(output, base=base) is None
        observations.append(ElementTree.fromstring(output.getvalue()).attrib.get(
            '{http://www.w3.org/XML/1998/namespace}base'))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('predicate', ['urn:p', 'urn:1p', 'urn:名', 'urn:p-1', 'urn:123'])
def test_xml11_qname_output_reparses_with_reference(predicate):
    observations = []
    for module in (rdflib, rdfcore):
        value = module.Graph().add((module.URIRef('urn:s'), module.URIRef(predicate),
                                    module.Literal('é😀\r\n\t')))
        try:
            output = value.serialize(format='xml')
        except ValueError:
            observations.append(ValueError)
        else:
            # Use the reference reader for both outputs; do not hide writer
            # errors behind matching defects in our own reader.
            actual = rdflib.Graph().parse(data=output, format='xml')
            assert set(actual) == {(rdflib.URIRef('urn:s'), rdflib.URIRef(predicate),
                                    rdflib.Literal('é😀\r\n\t'))}
            observations.append('roundtrip')
    assert observations[0] == observations[1]
