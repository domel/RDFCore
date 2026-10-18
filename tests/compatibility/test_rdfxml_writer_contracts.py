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
