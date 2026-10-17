"""Direct plugin tests; registration belongs to integration.

RDF 1.2 expectations target WD-rdf12-xml-20261009, sections 3.1,
5.1.2, 6.2.19 and 6.2.22 (Editor's Draft inspected 2026-10-17).
"""
from io import BytesIO

import pytest
import rdflib
from rdflib.compare import isomorphic

from rdfcore import Graph, URIRef, Literal, TripleTerm
from rdfcore.parser import create_input_source
from rdfcore.plugins.parsers.rdfxml import RDFXMLParser, RDFXML12Parser
from rdfcore.plugins.serializers.rdfxml import XMLSerializer, XML12Serializer

RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
EX = 'http://example.org/'


def test_registered_xml_plugins_roundtrip():
    graph = Graph().add((URIRef(EX+'s'), URIRef(EX+'p'), Literal('x')))
    for alias in ('xml', 'rdfxml', 'application/rdf+xml', 'xml12'):
        encoded = graph.serialize(format=alias)
        parsed = Graph().parse(data=encoded, format=alias)
        assert graph.isomorphic(parsed)


@pytest.mark.parametrize('encoding', [None, 'utf-8', 'utf-16'])
@pytest.mark.parametrize('destination', [False, True])
def test_xml12_announces_version_on_root(encoding, destination):
    from xml.etree import ElementTree
    graph = Graph().add((URIRef(EX+'s'), URIRef(EX+'p'), Literal('x')))
    if destination:
        stream = BytesIO()
        assert graph.serialize(stream, format='xml12', encoding=encoding) is graph
        encoded = stream.getvalue()
    else:
        encoded = graph.serialize(format='xml12', encoding=encoding)
    root = ElementTree.fromstring(encoded)
    assert root.tag == '{'+RDF+'}RDF'
    assert root.attrib['{'+RDF+'}version'] == '1.2'


def test_xml11_has_no_rdf12_announcement():
    from xml.etree import ElementTree
    root = ElementTree.fromstring(Graph().serialize(format='xml'))
    assert '{'+RDF+'}version' not in root.attrib


@pytest.mark.parametrize('format', ['xml', 'xml12'])
def test_xml_base_fragment_is_ignored(format):
    data = document('<rdf:Description rdf:about=""><ex:p rdf:resource="rel"/></rdf:Description>',
                    'xml:base="http://example.org/doc#fragment"')
    reference = rdflib.Graph().parse(data=data, format='xml')
    actual = Graph().parse(data=data, format=format)
    assert {(str(s), str(p), str(o)) for s, p, o in actual} == {
        (str(s), str(p), str(o)) for s, p, o in reference}
    assert next(iter(actual))[0] == URIRef('http://example.org/doc')


@pytest.mark.parametrize('suffix', ['.rdf', '.xml'])
def test_xml_file_format_detection_matches_reference(tmp_path, suffix):
    path = tmp_path / ('graph' + suffix)
    path.write_text(document('<rdf:Description rdf:about="urn:s"><ex:p>x</ex:p></rdf:Description>'))
    for module in (rdflib, __import__('rdfcore')):
        graph = module.Graph().parse(path)
        assert len(graph) == 1
        assert next(iter(graph))[0] == module.URIRef('urn:s')


def document(body, attrs=''):
    return f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:ex="{EX}" {attrs}>{body}</rdf:RDF>'


def parse(data, cls=RDFXMLParser, **kwargs):
    graph = Graph()
    cls().parse(create_input_source(data=data, publicID=EX), graph, **kwargs)
    return graph


@pytest.mark.parametrize('body', [
    '', '<rdf:Description rdf:about="s"><ex:p>hello</ex:p></rdf:Description>',
    '<ex:Thing rdf:ID="s" xml:lang="en" ex:name="Name"><rdf:li rdf:resource="o"/><rdf:li>two</rdf:li></ex:Thing>',
    '<rdf:Description rdf:about="s"><ex:p rdf:parseType="Resource"><ex:q>v</ex:q></ex:p></rdf:Description>',
    '<rdf:Description rdf:about="s"><ex:p rdf:parseType="Collection"><rdf:Description rdf:about="a"/><ex:Thing rdf:nodeID="b"/></ex:p></rdf:Description>',
    '<rdf:Description rdf:about="s"><ex:p ex:q="v" rdf:type="http://example.org/T"/></rdf:Description>',
    '<rdf:Description xml:base="sub/" rdf:about="s"><ex:p rdf:ID="statement" rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">0042</ex:p></rdf:Description>',
    '<rdf:Description rdf:about="s"><ex:p rdf:parseType="Literal"><ex:b>bold &amp; plain</ex:b></ex:p></rdf:Description>',
    '<rdf:Description rdf:nodeID="x"><ex:p rdf:nodeID="x"/><ex:q xml:lang="">v</ex:q></rdf:Description>',
])
def test_rdflib_differential(body):
    data = document(body)
    reference = rdflib.Graph().parse(data=data, format='xml', publicID=EX)
    graph = parse(data)
    serialized = XMLSerializer(graph).serialize()
    actual = rdflib.Graph().parse(data=serialized, format='xml', publicID=EX)
    assert isomorphic(reference, actual)
    assert len(graph) == len(reference)
    assert isomorphic(reference, rdflib.Graph().parse(
        data=XMLSerializer(parse(serialized)).serialize(), format='xml'))


@pytest.mark.parametrize('body', [
    '<rdf:Description rdf:about="s" rdf:nodeID="b"/>',
    '<rdf:Description rdf:nodeID="1bad"/>',
    '<rdf:Description><ex:p rdf:resource="a" rdf:nodeID="b"/></rdf:Description>',
    '<rdf:Description><ex:p rdf:parseType="Resource" rdf:datatype="d"/></rdf:Description>',
    '<rdf:Description><rdf:Description/></rdf:Description>',
    '<rdf:Description><ex:p><rdf:Description/><rdf:Description/></ex:p></rdf:Description>',
])
def test_invalid_shared(body):
    for action in (lambda: parse(document(body)), lambda: rdflib.Graph().parse(data=document(body), format='xml')):
        with pytest.raises(Exception):
            action()


@pytest.mark.parametrize('data', [
    '<!DOCTYPE x [<!ENTITY a "secret">]><x/>',
    '<!DOCTYPE x SYSTEM "https://example.invalid/evil"><x/>',
    '<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><x>&a;</x>',
])
@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_dtd_forbidden(data, encoding):
    with pytest.raises(Exception, match='DTD'):
        parse(data.encode(encoding))


def test_rdf12_nested_terms_annotations_direction():
    data = document('''<rdf:Description rdf:about="s">
      <ex:p rdf:annotationNodeID="r" xml:lang="ar" its:dir="rtl">text</ex:p>
      <ex:q rdf:parseType="Triple"><rdf:Description rdf:about="inner">
        <ex:p rdf:parseType="Triple"><rdf:Description rdf:about="deep"><ex:q>v</ex:q></rdf:Description></ex:p>
      </rdf:Description></ex:q>
    </rdf:Description>''', 'rdf:version="1.2" xmlns:its="http://www.w3.org/2005/11/its" its:version="2.0"')
    graph = parse(data, RDFXML12Parser)
    assert len(graph) == 3
    literal = graph.value(URIRef(EX+'s'), URIRef(EX+'p'))
    assert literal.direction == 'rtl' and literal.language == 'ar'
    term = graph.value(URIRef(EX+'s'), URIRef(EX+'q'))
    assert isinstance(term, TripleTerm) and isinstance(term.object, TripleTerm)
    assert (term.subject, term.predicate, term.object) not in graph
    result = parse(XML12Serializer(graph).serialize(), RDFXML12Parser, preserve_bnode_ids=True)
    assert len(result) == len(graph)
    assert result.value(URIRef(EX+'s'), URIRef(EX+'q')) == term
    with pytest.raises(ValueError):
        XMLSerializer(graph).serialize()


@pytest.mark.parametrize('body,attrs', [
    ('<rdf:Description><ex:p rdf:parseType="Triple"/></rdf:Description>', 'rdf:version="1.2"'),
    ('<rdf:Description><ex:p rdf:parseType="Triple"><rdf:Description><ex:p>a</ex:p><ex:q>b</ex:q></rdf:Description></ex:p></rdf:Description>', 'rdf:version="1.2"'),
    ('<rdf:Description><ex:p rdf:annotation="r">v</ex:p></rdf:Description>', ''),
    ('<rdf:Description><ex:p rdf:parseType="Triple"/></rdf:Description>', 'rdf:version="1.2-basic"'),
])
def test_invalid_rdf12(body, attrs):
    with pytest.raises(Exception):
        parse(document(body, attrs), RDFXML12Parser)


def test_stream_ownership_and_encoding():
    stream = BytesIO(document('').encode())
    RDFXMLParser().parse(create_input_source(file=stream), Graph())
    assert not stream.closed
    output = BytesIO()
    XMLSerializer(Graph()).serialize(output, encoding='utf-16')
    assert len(parse(output.getvalue())) == 0
