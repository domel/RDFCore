"""XML 1.1 Second Edition §§2.2, 2.11; RDF/XML WD 2026-10-09 §5.

XML12 transport extensions do not change the legacy RDFLib XML parser.
"""
from io import BytesIO
from xml.sax import SAXParseException

import pytest

import rdfcore
from rdfcore import Graph, Literal, RDF, URIRef


class ShortReads(BytesIO):
    def read(self, size=-1):
        assert size > 0
        return super().read(min(size, 1))


def document(text, declaration='1.1', encoding='UTF-8'):
    return (f'<?xml version="{declaration}" encoding="{encoding}"?>'
            f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" rdf:version="1.2">'
            '<rdf:Description rdf:about="urn:s"><e:p>'+text+
            '</e:p></rdf:Description></rdf:RDF>')


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be',
                                     'utf-32', 'utf-32-le', 'utf-32-be'])
@pytest.mark.parametrize('version', ['1.0', '1.1'])
def test_xml12_encoded_transport_and_short_reads(encoding, version):
    stream = ShortReads(document('é', version, encoding).encode(encoding))
    graph = Graph().parse(source=stream, format='xml12')
    assert set(graph) == {(URIRef('urn:s'), URIRef('urn:e:p'), Literal('é'))}
    assert not stream.closed


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16', 'utf-32'])
def test_xml11_character_references_and_line_ends(encoding):
    stream = ShortReads(document('a&#1;b\x85c\u2028d\r\x85e', encoding=encoding).encode(encoding))
    graph = Graph().parse(source=stream, format='xml12')
    assert str(graph.value(URIRef('urn:s'), URIRef('urn:e:p'))) == 'a\x01b\nc\nd\ne'


@pytest.mark.parametrize('value', ['\x01', '\x7f', '&#0;', '&#xD800;'])
def test_xml11_invalid_characters_are_rejected(value):
    with pytest.raises(SAXParseException):
        Graph().parse(data=document(value), format='xml12')


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16', 'utf-32'])
def test_transport_does_not_bypass_dtd_guard(encoding):
    source = document('&x;', encoding=encoding).replace('<rdf:RDF',
        '<!DOCTYPE rdf:RDF [<!ENTITY x SYSTEM "file:///not-to-read">]><rdf:RDF', 1)
    graph = Graph()
    with pytest.raises(SAXParseException, match='DTD'):
        graph.parse(source=ShortReads(source.encode(encoding)), format='xml12')
    assert len(graph) == 0


def test_xml10_does_not_acquire_xml11_character_space():
    with pytest.raises(SAXParseException):
        Graph().parse(data=document('&#1;', '1.0'), format='xml12')


@pytest.mark.parametrize('encoding,declared', [('utf-32', 'utf-8'), ('utf-16', 'utf-8'),
                                             ('utf-32-le', 'utf-32-be'), ('utf-32-be', 'utf-32-le'),
                                             ('utf-16-le', 'utf-16-be'), ('utf-16-be', 'utf-16-le')])
def test_encoding_declaration_mismatch_is_rejected(encoding, declared):
    with pytest.raises(SAXParseException, match='encoding declaration'):
        Graph().parse(data=document('v', encoding=declared).encode(encoding), format='xml12')


def test_placeholder_does_not_change_real_private_use_characters():
    graph = Graph().parse(data=document('&#1;\U000f0000&#xF0001;'), format='xml12')
    assert str(next(iter(graph))[2]) == '\x01\U000f0000\U000f0001'


@pytest.mark.parametrize('codepoint', [1, 2, 0x7f, 0x85, 0x2028])
def test_xml_literal_restricted_reference_stays_a_reference(codepoint):
    source = document('').replace('<e:p></e:p>',
        f'<e:p rdf:parseType="Literal"><a x="&#{codepoint};">&#{codepoint};</a></e:p>')
    graph = Graph().parse(data=source, format='xml12')
    value = graph.value(URIRef('urn:s'), URIRef('urn:e:p'))
    assert str(value) == f'<a x="&#{codepoint};">&#{codepoint};</a>'
    restored = Graph().parse(data=graph.serialize(format='xml12'), format='xml12')
    assert set(restored) == set(graph)


def test_legacy_utf32_retains_oracle_exception_and_stream_ownership():
    import rdflib
    source = document('v', '1.0', 'utf-32').encode('utf-32')
    for module in (rdflib, rdfcore):
        stream = ShortReads(source)
        with pytest.raises(SAXParseException):
            module.Graph().parse(source=stream, format='xml')
        # RDFLib owns its input source, but RDFCore's explicit security
        # extension promises not to close a caller-owned stream.
        if module.__name__ == 'rdfcore':
            assert not stream.closed
    with pytest.raises(SAXParseException, match='unsupported by the legacy XML parser'):
        Graph().parse(data=source, format='xml')


@pytest.mark.parametrize('format', ['xml', 'xml12'])
@pytest.mark.parametrize('error_type', [ValueError, OSError])
def test_input_failures_are_not_reclassified_as_xml_errors(format, error_type):
    error = error_type('input failure')
    class Broken(BytesIO):
        def read(self, size=-1):
            raise error
    stream = Broken(b'')
    with pytest.raises(error_type) as caught:
        Graph().parse(source=stream, format=format)
    assert caught.value is error
    assert not stream.closed


@pytest.mark.parametrize('separator', ['\x85', '\u2028'])
def test_xml11_line_separators_are_forbidden_inside_declaration(separator):
    source = document('v').replace(' encoding=', separator+'encoding=', 1)
    with pytest.raises(SAXParseException):
        Graph().parse(data=source, format='xml12')


def test_restricted_namespace_reference_cannot_leak_adapter_placeholder():
    source = document('v').replace('xmlns:e="urn:e:"', 'xmlns:e="urn:&#1;"')
    graph = Graph()
    with pytest.raises(SAXParseException, match='namespace IRI'):
        graph.parse(data=source, format='xml12')
    assert len(graph) == 0
