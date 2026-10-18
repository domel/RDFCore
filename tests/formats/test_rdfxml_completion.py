"""XML WD 2026-10-09 §§ 5.2, 6.2.19, 7; ED checked 2026-10-18.

Published-version cases remain independent of disputed archived fixtures.
Legacy shared behavior uses the executable RDFLib 7.6.0 oracle.
"""
import pytest
import rdflib
from xml.sax import SAXParseException

from rdfcore import Graph, Literal, RDF, TripleTerm, URIRef


def document(content, version='1.2'):
    return (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" '
            f'xmlns:xmlmeta="urn:metadata:" rdf:version="{version}">'
            f'{content}</rdf:RDF>')


def test_triple_production_adds_outer_triple_without_asserting_inner():
    data = document('<rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Triple">'
                    '<rdf:Description rdf:about="urn:a"><e:q rdf:resource="urn:b"/>'
                    '</rdf:Description></e:p></rdf:Description>')
    expected = (URIRef('urn:s'), URIRef('urn:p'),
                TripleTerm(URIRef('urn:a'), URIRef('urn:q'), URIRef('urn:b')))
    assert set(Graph().parse(data=data, format='xml12')) == {expected}


def test_direction_on_property_attribute_is_not_discarded():
    data = document('<rdf:Description rdf:about="urn:s" e:p="value"/>').replace(
        'rdf:version="1.2"', 'rdf:version="1.2" xml:lang="en" '
        'xmlns:its="http://www.w3.org/2005/11/its" its:dir="ltr"')
    assert set(Graph().parse(data=data, format='xml12')) == {
        (URIRef('urn:s'), URIRef('urn:p'), Literal('value', lang='en', direction='ltr'))}


def test_reserved_xml_names_do_not_become_rdf_events_in_xml12():
    data = document('<rdf:Description rdf:about="urn:s" xmlmeta:attribute="metadata">'
                    '<xmlmeta:property>metadata</xmlmeta:property>'
                    '<XMLmetadata/><e:p>value</e:p></rdf:Description>')
    assert set(Graph().parse(data=data, format='xml12')) == {
        (URIRef('urn:s'), URIRef('urn:p'), Literal('value'))}


def test_reserved_names_inside_xml_literals_are_not_filtered():
    data = document('<rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Literal">'
                    '<xmlmeta:a/><XMLmetadata/></e:p></rdf:Description>')
    value = Graph().parse(data=data, format='xml12').value(URIRef('urn:s'), URIRef('urn:p'))
    assert 'xmlmeta:a' in str(value) and '<XMLmetadata/>' in str(value)


def test_xml11_keeps_reference_reserved_prefix_attribute_behavior():
    data = document('<rdf:Description rdf:about="urn:s" xmlmeta:attribute="metadata"/>')
    data = data.replace('rdf:version="1.2"', '')
    def observe(module):
        return {(str(s), str(p), str(o)) for s, p, o in module.Graph().parse(data=data, format='xml')}
    assert observe(__import__('rdfcore')) == observe(rdflib)


@pytest.mark.parametrize('levels,accepted', [(126, True), (127, False)])
def test_xml12_writer_depth_limit_matches_parser_limit(levels, accepted):
    term = Literal('value')
    for _ in range(levels):
        term = TripleTerm(URIRef('urn:a'), URIRef('urn:q'), term)
    graph = Graph().add((URIRef('urn:s'), URIRef('urn:p'), term))
    if accepted:
        result = Graph().parse(data=graph.serialize(format='xml12'), format='xml12')
        assert set(result) == set(graph)
    else:
        with pytest.raises(ValueError, match='nesting'):
            graph.serialize(format='xml12')


@pytest.mark.parametrize('format', ['xml', 'xml12'])
def test_qnames_and_colliding_prefixes_preserve_rdf_meaning(format):
    graph = Graph()
    graph.bind('ns1', URIRef('urn:unrelated:'))
    graph.bind('rdf', URIRef('urn:not-rdf:'))
    for predicate in ('urn:p', 'urn:1p', 'urn:名', 'urn:p-1', 'http://example.org/a.b#name'):
        graph.add((URIRef('urn:s'), URIRef(predicate), Literal('é😀\r\n\t')))
    assert set(Graph().parse(data=graph.serialize(format=format), format=format)) == set(graph)


def test_unrepresentable_qname_error_matches_reference():
    for module in (rdflib, __import__('rdfcore')):
        graph = module.Graph().add((module.URIRef('urn:s'), module.URIRef('urn:123'), module.Literal('v')))
        with pytest.raises(ValueError):
            graph.serialize(format='xml')


def test_dtd_policy_difference_from_reference_is_explicit():
    data = '<!DOCTYPE rdf:RDF [<!ENTITY e "internal">]>' + document(
        '<rdf:Description rdf:about="urn:s"><e:p>&e;</e:p></rdf:Description>')
    data = data.replace('rdf:version="1.2"', '')
    reference = rdflib.Graph().parse(data=data, format='xml')
    assert reference.value(rdflib.URIRef('urn:s'), rdflib.URIRef('urn:p')) == rdflib.Literal('internal')
    with pytest.raises(SAXParseException, match='DTD'):
        Graph().parse(data=data, format='xml')
