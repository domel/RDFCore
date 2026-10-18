"""Concepts CR 2026-04-07, section 4.1 (also checked against ED 2026-10-18)."""
import pytest

from rdfcore import BNode, Dataset, Graph, Literal, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.interop import basic_decode, basic_encode, interop_downgrade


def graph_ids(dataset):
    return {graph.identifier for graph in dataset.graphs()}


@pytest.mark.parametrize('transform', [basic_encode, basic_decode, lambda d: interop_downgrade(d, '1.1'), lambda d: interop_downgrade(d, '1.2-basic')])
def test_interop_retains_empty_graphs(transform):
    dataset = Dataset()
    dataset.graph(URIRef('urn:empty'))
    dataset.graph(BNode('empty'))
    dataset.default_graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('x')))
    result = transform(dataset)
    assert graph_ids(result) == graph_ids(dataset)
    assert isomorphic(result, dataset)


def test_datasets_with_different_empty_graphs_are_not_isomorphic():
    a, b = Dataset(), Dataset()
    a.graph(URIRef('urn:a'))
    assert not isomorphic(a, b)
    b.graph(URIRef('urn:b'))
    assert not isomorphic(a, b)


def test_empty_graph_names_share_mapping_with_nested_terms():
    a, b = Dataset(), Dataset()
    p, s = URIRef('urn:p'), URIRef('urn:s')
    a.graph(BNode('a'))
    b.graph(BNode('b'))
    a.add((s, p, TripleTerm(BNode('a'), p, Literal('x'))))
    b.add((s, p, TripleTerm(BNode('b'), p, Literal('x'))))
    assert isomorphic(a, b)
    b.default_graph.set((s, p, TripleTerm(BNode('different'), p, Literal('x'))))
    assert not isomorphic(a, b)


def test_rdf12_method_still_uses_exact_structural_comparison():
    p, s = URIRef('urn:p'), URIRef('urn:s')
    a, b = Graph(), Graph()
    a.add((BNode('a'), p, TripleTerm(s, p, Literal('x'))))
    b.add((s, p, TripleTerm(BNode('b'), p, Literal('x'))))
    assert not a.isomorphic(b)


@pytest.mark.parametrize('format', ['turtle12', 'trig12', 'xml12'])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
def test_rdf12_serialization_base_round_trip(format, mode):
    # The RDF/XML serializer has no streaming mode; its ordinary path is used.
    graph = Dataset(default_graph_base='https://example.org/') if format == 'trig12' else Graph(base='https://example.org/')
    triple = (URIRef('https://example.org/s'), URIRef('https://example.org/p'),
              TripleTerm(URIRef('https://example.org/s'), URIRef('https://example.org/p'), Literal('text', lang='en', direction='rtl')))
    graph.add(triple)
    options = {'rdf_version': '1.2'}
    if format != 'xml12': options['mode'] = mode
    data = graph.serialize(format=format, encoding='utf-8', **options)
    assert (b'xml:base=' if format == 'xml12' else b'@base') in data
    restored = (Dataset() if format == 'trig12' else Graph()).parse(data=data, format=format, publicID='https://unrelated/')
    assert isomorphic(graph, restored)
