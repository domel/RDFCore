from rdfcore import BNode, Graph, Literal, URIRef


def test_graph_isomorphic_is_method_backed_by_compare():
    predicate = URIRef("urn:p")
    left = Graph().add((BNode("left"), predicate, Literal("x")))
    right = Graph().add((BNode("right"), predicate, Literal("x")))
    assert left.isomorphic(right)


def test_triples_choices_accepts_choices_in_any_position():
    graph = Graph()
    subjects = [URIRef("urn:s1"), URIRef("urn:s2")]
    predicates = [URIRef("urn:p1"), URIRef("urn:p2")]
    for subject in subjects:
        for predicate in predicates:
            graph.add((subject, predicate, Literal("x")))
    assert len(list(graph.triples_choices((subjects, predicates, Literal("x"))))) == 4
