"""S09 T29: XML WD 2026-10-09 conflicts, ED checked 2026-10-18.

Small offline witnesses for all 17 reviewed annotation constructions.
The official fixture files and their expected results are never rewritten.
"""
import pytest
from xml.sax import SAXParseException

from rdfcore import BNode, Graph, Literal, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic

S, P, Q, O, R = map(URIRef, ('urn:s', 'urn:p', 'urn:q', 'urn:o', 'urn:r'))


def annotation_case(name):
    subject, predicate, obj, reifier = S, P, Literal('blah'), R
    attrs, content, extra, tail = 'rdf:annotation="urn:r"', 'blah', [], ''
    if name in ('02', '12', '14', '16'):
        attrs, reifier = 'rdf:annotationNodeID="r"', BNode('r')
    if name in ('11', '12'):
        subject = BNode('s')
    if name == '03':
        tail = '<rdf:Description rdf:about="urn:r"><e:q>metadata</e:q></rdf:Description>'
        extra.append((R, Q, Literal('metadata')))
    if name in ('04', '05', '06'):
        obj, content = BNode('o'), ''
        attrs += {'04': ' rdf:nodeID="o"', '05': ' rdf:parseType="Resource"',
                  '06': ' e:q="extra"'}[name]
        if name == '06':
            extra.append((obj, Q, Literal('extra')))
    if name in ('07', '08', '09'):
        obj, content = (BNode('o') if name == '09' else O), ''
        attrs += ' rdf:nodeID="o"' if name == '09' else ' rdf:resource="urn:o"'
        if name == '07':
            predicate = RDF.type
    if name == '10':
        obj = O
        content = ('<rdf:Description rdf:about="urn:o">'
                   '<e:q rdf:annotation="urn:inner">inner</e:q></rdf:Description>')
        extra += [(O, Q, Literal('inner')),
                  (URIRef('urn:inner'), RDF.reifies, TripleTerm(O, Q, Literal('inner')))]
    if name in ('13', '14'):
        attrs += ' rdf:parseType="Literal"'
        obj, content = Literal('<b/>', datatype=RDF.XMLLiteral), '<b/>'
    if name in ('15', '16'):
        attrs += ' rdf:parseType="Collection"'
        obj, content = BNode('cell'), '<rdf:Description rdf:about="urn:o"/>'
        extra += [(obj, RDF.first, O), (obj, RDF.rest, RDF.nil)]
    if name == 'reif-01':
        attrs += ' rdf:ID="statement"'
        statement = URIRef('https://example.org/doc#statement')
        extra += [(statement, RDF.type, RDF.Statement), (statement, RDF.subject, S),
                  (statement, RDF.predicate, P), (statement, RDF.object, obj)]
    tag = 'rdf:type' if predicate == RDF.type else 'e:p'
    identity = 'rdf:nodeID="s"' if isinstance(subject, BNode) else 'rdf:about="urn:s"'
    body = f'<rdf:Description {identity}><{tag} {attrs}>{content}</{tag}></rdf:Description>{tail}'
    expected = Graph()
    for triple in [(subject, predicate, obj),
                   (reifier, RDF.reifies, TripleTerm(subject, predicate, obj)), *extra]:
        expected.add(triple)
    return body, expected


@pytest.mark.parametrize('name', [f'{i:02}' for i in range(1, 17)] + ['reif-01'])
def test_each_archived_annotation_has_distinct_default_and_recovery_profiles(name):
    body, expected = annotation_case(name)
    data = (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" '
            f'xml:base="https://example.org/doc">{body}</rdf:RDF>')
    with pytest.raises(SAXParseException, match='require rdf:version'):
        Graph().parse(data=data, format='xml12')
    # Verify a per-call recovery option does not leak into subsequent parsing.
    recovered = Graph().parse(data=data, format='xml12', legacy_w3c=True)
    # Recovery expands empty XMLLiteral elements, deliberately changing lexical identity.
    if name in ('13', '14'):
        literal = Literal('<b></b>', datatype=RDF.XMLLiteral)
        reifier = R if name == '13' else BNode('r')
        legacy_expected = Graph().add((S, P, literal)).add(
            (reifier, RDF.reifies, TripleTerm(S, P, literal)))
    else:
        legacy_expected = expected
    assert len(recovered) == len(legacy_expected)
    assert isomorphic(recovered, legacy_expected)
    announced = data.replace('<rdf:RDF ', '<rdf:RDF rdf:version="1.2" ', 1)
    actual = Graph().parse(data=announced, format='xml12')
    assert len(actual) == len(expected)
    assert isomorphic(actual, expected)
    with pytest.raises(SAXParseException, match='require rdf:version'):
        Graph().parse(data=data, format='xml12')


@pytest.mark.parametrize('legacy', [False, True])
def test_disputed_direction_property_attribute_never_loses_direction(legacy):
    data = (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" '
            'xmlns:its="http://www.w3.org/2005/11/its" its:dir="ltr" '
            'xml:lang="en" rdf:version="1.2">'
            '<rdf:Description rdf:about="urn:s" e:p="bar"/></rdf:RDF>')
    assert set(Graph().parse(data=data, format='xml12', legacy_w3c=legacy)) == {
        (S, P, Literal('bar', lang='en', direction='ltr'))}


@pytest.mark.parametrize('legacy', [False, True])
def test_disputed_triple_result_is_one_outer_assertion_not_an_empty_graph(legacy):
    data = (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" rdf:version="1.2">'
            '<rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Triple">'
            '<rdf:Description rdf:about="urn:o"><e:q>inner</e:q></rdf:Description>'
            '</e:p></rdf:Description></rdf:RDF>')
    assert set(Graph().parse(data=data, format='xml12', legacy_w3c=legacy)) == {
        (S, P, TripleTerm(O, Q, Literal('inner')))}


@pytest.mark.parametrize('attribute', ['rdf:ID="statement"', 'rdf:annotation="urn:r"',
                                       'rdf:annotationNodeID="r"'])
@pytest.mark.parametrize('legacy', [False, True])
def test_detailed_triple_production_attribute_rule_wins_over_summary(attribute, legacy):
    # § 6.1 permits these attributes; § 6.2.19 does not. Keep the selected
    # detailed-production rule explicit, including in archived recovery.
    data = (f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:" rdf:version="1.2">'
            f'<rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Triple" {attribute}>'
            '<rdf:Description rdf:about="urn:o"><e:q>inner</e:q></rdf:Description>'
            '</e:p></rdf:Description></rdf:RDF>')
    with pytest.raises(SAXParseException, match='Triple production permits only'):
        Graph().parse(data=data, format='xml12', legacy_w3c=legacy)
