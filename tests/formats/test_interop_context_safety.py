"""Explicit interoperability must preserve graph-local definitions and data."""
import pytest

from rdfcore import BNode, Dataset, Graph, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.interop import basic_decode, basic_encode


def test_same_triple_term_in_two_graphs_round_trips():
    dataset = Dataset()
    term = TripleTerm(BNode('shared'), URIRef('urn:p'), URIRef('urn:o'))
    for name in (URIRef('urn:g1'), URIRef('urn:g2'), None):
        triple = (URIRef('urn:s'), RDF.reifies, term)
        if name is None:
            dataset.add(triple)
        else:
            dataset.add((*triple, name))
    encoded = basic_encode(dataset)
    assert isomorphic(dataset, basic_decode(encoded))
    for name in (URIRef('urn:g1'), URIRef('urn:g2'), None):
        graph = encoded.default_graph if name is None else encoded.graph(name)
        assert len(list(graph.subjects(RDF.type, RDF.PropositionForm))) == 1


def form_graph():
    graph = Graph()
    node = BNode('form')
    graph.add((URIRef('urn:s'), RDF.reifies, node))
    graph.add((node, RDF.type, RDF.PropositionForm))
    graph.add((node, RDF.propositionFormSubject, URIRef('urn:s')))
    graph.add((node, RDF.propositionFormPredicate, URIRef('urn:p')))
    graph.add((node, RDF.propositionFormObject, URIRef('urn:o')))
    return graph, node


def test_ambiguous_form_is_rejected_without_mutation():
    graph, node = form_graph()
    graph.add((node, RDF.propositionFormObject, URIRef('urn:other')))
    before = set(graph)
    with pytest.raises(ValueError, match='ambiguous'):
        basic_decode(graph)
    assert set(graph) == before


def test_cyclic_form_is_rejected_explicitly():
    graph, node = form_graph()
    graph.set((node, RDF.propositionFormObject, node))
    with pytest.raises(ValueError, match='cyclic'):
        basic_decode(graph)
