from rdfcore import BNode, Dataset, Graph, URIRef
from rdfcore.compare import isomorphic
from rdfcore.term import TripleTerm


def test_isomorphic_maps_blank_nodes_inside_nested_triple_terms():
    p = URIRef("urn:p")
    q = URIRef("urn:q")
    left, right = Graph(), Graph()
    a, b = BNode("a"), BNode("b")
    c, d = BNode("c"), BNode("d")
    left.add((a, p, TripleTerm(b, q, TripleTerm(a, q, b))))
    right.add((c, p, TripleTerm(d, q, TripleTerm(c, q, d))))
    assert isomorphic(left, right)


def test_dataset_isomorphism_maps_graph_and_embedded_blank_nodes_together():
    p = URIRef("urn:p")
    q = URIRef("urn:q")
    left, right = Dataset(), Dataset()
    subject, graph = BNode("subject"), BNode("graph")
    other_subject, other_graph = BNode("other-subject"), BNode("other-graph")
    left.add((subject, p, TripleTerm(graph, q, subject), graph))
    right.add((other_subject, p, TripleTerm(other_graph, q, other_subject), other_graph))
    assert isomorphic(left, right)


def test_isomorphism_rejects_inconsistent_mapping_between_outer_and_inner_terms():
    p = URIRef("urn:p")
    left, right = Graph(), Graph()
    left.add((BNode("a"), p, TripleTerm(BNode("b"), p, BNode("a"))))
    right.add((BNode("x"), p, TripleTerm(BNode("y"), p, BNode("z"))))
    assert not isomorphic(left, right)
