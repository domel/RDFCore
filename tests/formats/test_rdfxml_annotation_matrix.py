"""XML WD 2026-10-09 §§ 6.2.15-22; ED checked 2026-10-18.

These inline regressions keep the selected published-version expectations
independent of the pre-announcement official XML annotation fixtures.
"""
import pytest
from xml.sax import SAXParseException

from rdfcore import BNode, Graph, Literal, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic

BASE = 'https://example.org/doc'
S, P, Q, O = map(URIRef, ['urn:s', 'urn:p', 'urn:q', 'urn:o'])


def document(body, version='1.2'):
    return (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" '
            f'xml:base="{BASE}" rdf:version="{version}">'
            f'<rdf:Description rdf:about="urn:s">{body}</rdf:Description></rdf:RDF>')


@pytest.mark.parametrize('identifier', ['rdf:annotation="#r"', 'rdf:annotationNodeID="r"'])
@pytest.mark.parametrize('form', ['literal', 'empty', 'resource', 'node',
                                  'attributes', 'resource-block', 'nested',
                                  'collection', 'empty-collection', 'xml-literal'])
@pytest.mark.parametrize('statement_id', [False, True])
@pytest.mark.parametrize('predicate', [P, RDF.type])
def test_annotation_expansion_is_exact(form, identifier, statement_id, predicate):
    obj = Literal('value')
    attrs, content, extra = '', 'value', []
    if form == 'empty':
        obj, content = Literal(''), ''
    elif form == 'resource':
        obj, attrs, content = O, 'rdf:resource="urn:o"', ''
    elif form == 'node':
        obj, attrs, content = BNode('o'), 'rdf:nodeID="o"', ''
    elif form == 'attributes':
        obj, attrs, content = BNode('o'), 'e:q="extra"', ''
        extra = [(obj, Q, Literal('extra'))]
    elif form == 'resource-block':
        obj, attrs, content = BNode('o'), 'rdf:parseType="Resource"', '<e:q>extra</e:q>'
        extra = [(obj, Q, Literal('extra'))]
    elif form == 'nested':
        obj, content = O, '<rdf:Description rdf:about="urn:o"><e:q>extra</e:q></rdf:Description>'
        extra = [(O, Q, Literal('extra'))]
    elif form == 'collection':
        obj, attrs = BNode('cell'), 'rdf:parseType="Collection"'
        content = '<rdf:Description rdf:about="urn:o"/>'
        extra = [(obj, RDF.first, O), (obj, RDF.rest, RDF.nil)]
    elif form == 'empty-collection':
        obj, attrs, content = RDF.nil, 'rdf:parseType="Collection"', ''
    elif form == 'xml-literal':
        obj, attrs, content = Literal('<b/>', datatype=RDF.XMLLiteral), 'rdf:parseType="Literal"', '<b/>'
    reifier = BNode('r') if 'NodeID' in identifier else URIRef(BASE+'#r')
    expected = Graph()
    for triple in [(S, predicate, obj), (reifier, RDF.reifies, TripleTerm(S, predicate, obj)), *extra]:
        expected.add(triple)
    if statement_id:
        statement = URIRef(BASE+'#statement')
        for triple in [(statement, RDF.type, RDF.Statement), (statement, RDF.subject, S),
                       (statement, RDF.predicate, predicate), (statement, RDF.object, obj)]:
            expected.add(triple)
    sid = 'rdf:ID="statement"' if statement_id else ''
    tag = 'rdf:type' if predicate == RDF.type else 'e:p'
    body = f'<{tag} {identifier} {attrs} {sid}>{content}</{tag}>'
    actual = Graph().parse(data=document(body), format='xml12')
    assert len(actual) == len(expected)
    assert isomorphic(actual, expected)
    assert isomorphic(Graph().parse(data=actual.serialize(format='xml12'), format='xml12'), expected)


@pytest.mark.parametrize('version', ['1.1', '1.2-basic'])
@pytest.mark.parametrize('identifier', ['rdf:annotation="#r"', 'rdf:annotationNodeID="r"'])
def test_annotation_requires_full_profile_even_with_mime_version(version, identifier):
    with pytest.raises(SAXParseException, match='annotations require'):
        Graph().parse(data=document(f'<e:p {identifier}>value</e:p>', version),
                      format='application/rdf+xml; version=1.2')


@pytest.mark.parametrize('identifier', [
    'rdf:annotation="#r" rdf:annotationNodeID="r"',
    'rdf:annotationNodeID="1bad"',
])
def test_annotation_identifiers_reject_conflict_and_invalid_ncname(identifier):
    with pytest.raises(SAXParseException):
        Graph().parse(data=document(f'<e:p {identifier}>value</e:p>'), format='xml12')


def test_nested_annotations_keep_both_reifiers_and_shared_node_identity():
    body = ('<e:p rdf:annotationNodeID="outer"><rdf:Description rdf:nodeID="shared">'
            '<e:q rdf:annotationNodeID="inner" rdf:nodeID="shared"/>'
            '</rdf:Description></e:p>')
    data = document(body).replace('</rdf:RDF>',
        '<rdf:Description rdf:nodeID="outer"><e:q>metadata</e:q></rdf:Description></rdf:RDF>')
    expected = Graph()
    shared, outer, inner = map(BNode, ['shared', 'outer', 'inner'])
    for triple in [(S, P, shared), (shared, Q, shared),
                   (outer, RDF.reifies, TripleTerm(S, P, shared)),
                   (inner, RDF.reifies, TripleTerm(shared, Q, shared)),
                   (outer, Q, Literal('metadata'))]:
        expected.add(triple)
    actual = Graph().parse(data=data, format='xml12')
    assert len(actual) == 5
    assert isomorphic(actual, expected)
