"""Security policy and input ownership for the tree-based XML plugins."""
import builtins
from io import BytesIO
import socket
from xml.sax import SAXParseException

import pytest

from rdfcore import Graph, RDF
from rdfcore.parser import create_input_source
from rdfcore.plugins.parsers.rdfxml import RDFXMLParser, RDFXML12Parser


class Chunked(BytesIO):
    def __init__(self, data, chunk_size):
        super().__init__(data)
        self.chunk_size = chunk_size

    def read(self, size=-1):
        assert size > 0
        return super().read(min(size, self.chunk_size))


def document(content=''):
    return (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:">'
            f'<rdf:Description rdf:about="urn:s">{content}'
            '</rdf:Description></rdf:RDF>')


@pytest.mark.parametrize('parser_class', [RDFXMLParser, RDFXML12Parser])
@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
@pytest.mark.parametrize('chunk_size', [1, 7, 65536])
@pytest.mark.parametrize('declaration', [
    '<!DOCTYPE rdf:RDF [<!ENTITY x "internal">]>',
    '<!DOCTYPE rdf:RDF SYSTEM "http://127.0.0.1:9/external">',
    '<!DOCTYPE rdf:RDF [<!ENTITY x SYSTEM "{secret}">]>',
])
def test_dtd_rejected_before_external_access_and_parser_can_be_reused(
        tmp_path, monkeypatch, parser_class, encoding, chunk_size, declaration):
    secret = tmp_path / 'secret.txt'
    secret.write_text('not RDF input')
    original_open = builtins.open

    def guarded_open(path, *args, **kwargs):
        assert str(path) not in {str(secret), secret.as_uri()}
        return original_open(path, *args, **kwargs)

    def forbidden_network(*args, **kwargs):
        pytest.fail('XML document attempted network access')

    monkeypatch.setattr(builtins, 'open', guarded_open)
    monkeypatch.setattr(socket, 'create_connection', forbidden_network)
    monkeypatch.setattr(socket.socket, 'connect', forbidden_network)
    parser = parser_class()
    data = declaration.format(secret=secret.as_uri()) + document('<e:p>&x;</e:p>')
    source = Chunked(data.encode(encoding), chunk_size)
    sink = Graph()
    with pytest.raises(SAXParseException, match='DTD'):
        parser.parse(create_input_source(file=source), sink)
    assert not source.closed
    assert len(sink) == 0
    valid = Chunked(document('<e:p>safe</e:p>').encode(encoding), chunk_size)
    parser.parse(create_input_source(file=valid), sink)
    assert len(sink) == 1
    assert not valid.closed


@pytest.mark.parametrize('format', ['xml', 'xml12'])
@pytest.mark.parametrize('levels,accepted', [(253, True), (254, False)])
def test_xml_nesting_limit_at_boundary(format, levels, accepted):
    content = '<e:p rdf:parseType="Literal">' + '<a>'*levels + '</a>'*levels + '</e:p>'
    if accepted:
        assert len(Graph().parse(data=document(content), format=format)) == 1
    else:
        with pytest.raises(SAXParseException, match='depth of 256'):
            Graph().parse(data=document(content), format=format)


@pytest.mark.parametrize('format', ['xml', 'xml12'])
def test_large_xml_text_survives_input_chunk_boundaries(format):
    text = 'é' * 131073
    source = Chunked(document('<e:p>'+text+'</e:p>').encode(), 127)
    graph = Graph().parse(source=source, format=format)
    assert str(next(iter(graph))[2]) == text
    assert not source.closed
