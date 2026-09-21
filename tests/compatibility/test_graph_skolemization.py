from rdfcore import BNode, Graph, Literal, TripleTerm, URIRef


def test_bnode_skolemization_round_trips():
    blank = BNode("node")
    skolem = blank.skolemize()
    assert skolem == URIRef("https://rdflib.github.io/.well-known/genid/rdflib/node")
    assert skolem.de_skolemize() == blank


def test_graph_skolemization_maps_nested_triple_terms():
    graph = Graph()
    blank = BNode("node")
    embedded = TripleTerm(blank, URIRef("urn:p"), Literal("x"))
    graph.add((blank, URIRef("urn:outer"), embedded))
    skolemized = graph.skolemize()
    assert all(not isinstance(term, BNode) for triple in skolemized for term in triple[:2])
    restored = skolemized.de_skolemize()
    assert restored.isomorphic(graph)


def test_graph_skolemize_can_target_one_bnode():
    graph = Graph()
    selected, other = BNode("selected"), BNode("other")
    graph.add((selected, URIRef("urn:p"), other))
    result = graph.skolemize(bnode=selected)
    assert any(isinstance(subject, URIRef) for subject, _, _ in result)
    assert any(isinstance(obj, BNode) for _, _, obj in result)


def test_selective_skolemization_visits_nested_triple_terms():
    selected = BNode("selected")
    graph = Graph().add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(selected, URIRef("urn:q"), Literal("x"))))
    result = graph.skolemize(bnode=selected)
    assert isinstance(next(iter(result))[2].subject, URIRef)
    assert result.de_skolemize(uriref=selected.skolemize()).isomorphic(graph)
