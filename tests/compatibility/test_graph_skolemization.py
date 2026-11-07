from rdfcore import BNode, Graph, Literal, TripleTerm, URIRef


def test_graph_skolemization_maps_nested_triple_terms():
    graph = Graph()
    blank = BNode("node")
    embedded = TripleTerm(blank, URIRef("urn:p"), Literal("x"))
    graph.add((blank, URIRef("urn:outer"), embedded))
    skolemized = graph.skolemize()
    assert all(
        not isinstance(term, BNode) for triple in skolemized for term in triple[:2]
    )
    restored = skolemized.de_skolemize()
    assert restored.isomorphic(graph)
