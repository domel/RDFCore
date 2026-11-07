"""Explicit interoperability must preserve graph-local definitions and data."""

from rdfcore import BNode, Dataset, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.interop import basic_decode, basic_encode


def test_same_triple_term_in_two_graphs_round_trips():
    dataset = Dataset()
    term = TripleTerm(BNode("shared"), URIRef("urn:p"), URIRef("urn:o"))
    for name in (URIRef("urn:g1"), URIRef("urn:g2"), None):
        triple = (URIRef("urn:s"), RDF.reifies, term)
        if name is None:
            dataset.add(triple)
        else:
            dataset.add((*triple, name))
    encoded = basic_encode(dataset)
    assert isomorphic(dataset, basic_decode(encoded))
    for name in (URIRef("urn:g1"), URIRef("urn:g2"), None):
        graph = encoded.default_graph if name is None else encoded.graph(name)
        assert len(list(graph.subjects(RDF.type, RDF.PropositionForm))) == 1
