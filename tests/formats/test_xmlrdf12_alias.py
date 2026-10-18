"""The xmlrdf12 plugin alias must be identical to xml12, not a new syntax."""
import pytest

from rdfcore import Graph, Literal, TripleTerm, URIRef, plugin
from rdfcore.compare import isomorphic
from rdfcore.parser import Parser
from rdfcore.serializer import Serializer


@pytest.mark.parametrize('kind', [Parser, Serializer])
def test_xmlrdf12_resolves_to_existing_xml12_class(kind):
    assert plugin.get('xmlrdf12', kind).getClass() is plugin.get('xml12', kind).getClass()


@pytest.mark.parametrize('empty', [False, True])
@pytest.mark.parametrize('encoding', [None, 'utf-8'])
def test_xmlrdf12_round_trip_and_output_match_xml12(empty, encoding):
    graph = Graph()
    if not empty:
        graph.add((URIRef('urn:s'), URIRef('urn:p'), TripleTerm(
            URIRef('urn:a'), URIRef('urn:b'), Literal('text', lang='en', direction='rtl'))))
    output = graph.serialize(format='xmlrdf12', encoding=encoding)
    assert output == graph.serialize(format='xml12', encoding=encoding)
    restored = Graph()
    assert restored.parse(data=output, format='xmlrdf12') is restored
    assert isomorphic(graph, restored)


def test_xmlrdf12_rejects_rdf12_terms_in_explicit_legacy_profile():
    graph = Graph().add((URIRef('urn:s'), URIRef('urn:p'), Literal('text', lang='en', direction='rtl')))
    with pytest.raises(ValueError):
        graph.serialize(format='xmlrdf12', rdf_version='1.1')


def test_xmlrdf12_invalid_input_matches_existing_alias():
    errors = []
    for alias in ('xml12', 'xmlrdf12'):
        with pytest.raises(Exception) as caught:
            Graph().parse(data='<broken', format=alias)
        errors.append(type(caught.value))
    assert errors[0] is errors[1]
