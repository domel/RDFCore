"""Selected RDF/XML WD 2026-10-09 §§5.1.2, 6.2 scope rules.

Editor's Draft checked 2026-10-22; Triple conflicts retain the existing
explicit decision in test_rdfxml_conflict_profiles.py.
"""
import pytest
from xml.sax import SAXParseException

from rdfcore import Dataset, Graph, Literal, RDF, TripleTerm, URIRef


def document(body, version='1.2'):
    return (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" '
            'xmlns:its="http://www.w3.org/2005/11/its" '
            f'rdf:version="{version}" xml:base="https://example/a/" '
            f'xml:lang="en" its:dir="rtl">{body}</rdf:RDF>')


@pytest.mark.parametrize('version', ['1.2', '1.2-basic'])
@pytest.mark.parametrize('attributes,expected', [
    ('', Literal('v', lang='en', direction='rtl')),
    ('xml:lang=""', Literal('v')),
    ('its:dir=""', Literal('v', lang='en')),
    ('xml:lang="pl" its:dir="ltr"', Literal('v', lang='pl', direction='ltr')),
    ('rdf:datatype="urn:datatype"', Literal('v', datatype=URIRef('urn:datatype'))),
])
def test_context_override_is_local_and_does_not_leak_to_sibling(version, attributes, expected):
    graph = Graph().parse(data=document(
        '<rdf:Description rdf:about="s">'
        f'<e:p {attributes}>v</e:p><e:q>v</e:q></rdf:Description>', version), format='xml12')
    subject = URIRef('https://example/a/s')
    assert graph.value(subject, URIRef('urn:e:p')) == expected
    assert graph.value(subject, URIRef('urn:e:q')) == Literal('v', lang='en', direction='rtl')


def test_nested_resource_base_annotation_and_target_graph():
    dataset = Dataset()
    target = dataset.graph(URIRef('urn:target'))
    target.parse(data=document(
        '<rdf:Description rdf:about="s"><e:p rdf:parseType="Resource" xml:base="../b/">'
        '<e:q rdf:resource="o" rdf:annotation="reifier"/>'
        '</e:p></rdf:Description>'), format='xml12')
    inner = target.value(URIRef('https://example/a/s'), URIRef('urn:e:p'))
    triple = (inner, URIRef('urn:e:q'), URIRef('https://example/b/o'))
    assert triple in target
    assert (URIRef('https://example/b/reifier'), RDF.reifies, TripleTerm(*triple)) in target
    assert len(target) == 3
    assert len(dataset.default_graph) == 0


@pytest.mark.parametrize('attributes', [
    'rdf:resource="urn:o" rdf:nodeID="b"',
    'rdf:resource="urn:o" rdf:datatype="urn:d"',
    'rdf:nodeID="b" rdf:datatype="urn:d"',
    'rdf:parseType="Resource" rdf:resource="urn:o"',
    'rdf:parseType="Collection" rdf:nodeID="b"',
    'rdf:annotation="urn:r" rdf:annotationNodeID="b"',
    'rdf:nodeID="invalid:name"',
    'rdf:ID="invalid:name"',
    'its:dir="auto"',
    'rdf:version="unknown"',
])
def test_invalid_attribute_combinations_are_not_legacy_compatibility(attributes):
    with pytest.raises(SAXParseException):
        Graph().parse(data=document(
            f'<rdf:Description><e:p {attributes}/></rdf:Description>'), format='xml12')


def test_profile_override_does_not_enable_annotations_in_basic():
    source = document('<rdf:Description><e:p rdf:version="1.2-basic" '
                      'rdf:annotation="urn:r">v</e:p></rdf:Description>')
    with pytest.raises(SAXParseException, match='annotations require'):
        Graph().parse(data=source, format='application/rdf+xml; version=1.2')


@pytest.mark.parametrize('options', [{'format': 'xml', 'strict': True}, {'format': 'xml12'}])
def test_normative_property_ids_are_unique(options):
    source = document('<rdf:Description><e:p rdf:ID="x">v</e:p>'
                      '<e:q rdf:ID="x">w</e:q></rdf:Description>')
    if options['format'] == 'xml':
        source = source.replace('rdf:version="1.2"', '').replace('its:dir="rtl"', '')
    with pytest.raises(SAXParseException, match='duplicate rdf:ID'):
        Graph().parse(data=source, **options)
