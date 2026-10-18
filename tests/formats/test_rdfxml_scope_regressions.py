"""XML12: WD-rdf12-xml-20261009 §§ 5.1.2, 6.2.12 and 6.2.17.

The corresponding Editor's Draft was inspected on 2026-10-18.
XML11 lexical compatibility is tested separately against RDFLib 7.6.0.
"""
import pytest
from xml.sax import SAXParseException

from rdfcore import Graph, Literal, RDF, URIRef


def document(content):
    return (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" '
            f'rdf:version="1.2"><rdf:Description rdf:about="urn:s">'
            f'{content}</rdf:Description></rdf:RDF>')


@pytest.mark.parametrize('fragment,expected', [
    ('text&#13;more', 'text\rmore'),
    ('<a xmlns="urn:a"><b xmlns=""/></a>',
     '<a xmlns="urn:a"><b xmlns=""/></a>'),
    ('<!--comment--><?target data?><a/>', '<!--comment--><?target data?><a/>'),
])
def test_xml12_keeps_literal_information_separate_from_legacy(fragment, expected):
    graph = Graph().parse(data=document(
        f'<e:p rdf:parseType="Literal">{fragment}</e:p>'), format='xml12')
    value = graph.value(URIRef('urn:s'), URIRef('urn:e:p'))
    assert str(value) == expected
    assert value.datatype == RDF.XMLLiteral
    restored = Graph().parse(data=graph.serialize(format='xml12'), format='xml12')
    assert set(restored) == set(graph)


@pytest.mark.parametrize('space', ['\u00a0', '\u2003', '\u2028'])
@pytest.mark.parametrize('content', [
    '{space}<e:p>v</e:p>',
    '<e:p rdf:parseType="Resource">{space}</e:p>',
    '<e:p rdf:parseType="Collection">{space}</e:p>',
])
def test_xml12_structural_whitespace_is_xml_whitespace(space, content):
    with pytest.raises(SAXParseException, match='unexpected text'):
        Graph().parse(data=document(content.format(space=space)), format='xml12')


@pytest.mark.parametrize('space', [' ', '\t', '\r', '\n'])
def test_xml12_accepts_xml_structural_whitespace(space):
    graph = Graph().parse(data=document(space+'<e:p>v</e:p>'+space), format='xml12')
    assert set(graph) == {(URIRef('urn:s'), URIRef('urn:e:p'), Literal('v'))}
