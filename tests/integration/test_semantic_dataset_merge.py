"""Semantics CRD 2026-09-24 §10, Definition of RDF dataset merge."""

from rdfcore import BNode, Dataset, Literal, TripleTerm, URIRef
from rdfcore.semantics import merge_datasets

P, G = URIRef("urn:p"), URIRef("urn:g")


def test_merge_standardizes_apart_and_preserves_sharing_inside_each_dataset():
    inputs = [Dataset(), Dataset()]
    shared = BNode("shared")
    for dataset in inputs:
        dataset.default_graph.add((shared, P, Literal("default")))
        dataset.graph(G).add((shared, P, TripleTerm(shared, P, shared)))
        dataset.graph(shared).add((shared, P, Literal("named")))
    before = [set(d.quads()) for d in inputs]
    merged = merge_datasets(iter(inputs))
    nodes = set(merged.default_graph.subjects(P, Literal("default")))
    assert len(nodes) == 2 and all(isinstance(n, BNode) for n in nodes)
    assert shared not in nodes
    assert len(merged) == 6
    for node in nodes:
        assert (node, P, TripleTerm(node, P, node)) in merged.graph(G)
        assert (node, P, Literal("named")) in merged.graph(node)
    assert [set(d.quads()) for d in inputs] == before
