from rdfcore import BNode, Graph, Literal, URIRef


def test_graph_isomorphic_is_method_backed_by_compare():
    predicate = URIRef("urn:p")
    left = Graph().add((BNode("left"), predicate, Literal("x")))
    right = Graph().add((BNode("right"), predicate, Literal("x")))
    assert left.isomorphic(right)
