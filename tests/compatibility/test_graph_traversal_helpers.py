from rdfcore import Graph, URIRef


def test_transitive_helpers_follow_cycles_once():
    graph = Graph()
    predicate = URIRef("urn:next")
    nodes = [URIRef(f"urn:{name}") for name in "abc"]
    for left, right in zip(nodes, nodes[1:] + nodes[:1]):
        graph.add((left, predicate, right))
    assert set(graph.transitive_objects(nodes[0], predicate)) == set(nodes)
    assert set(graph.transitive_subjects(predicate, nodes[0])) == set(nodes)
    assert set(
        graph.transitiveClosure(lambda node, g: g.objects(node, predicate), nodes[0])
    ) == set(nodes)


def test_connected_and_all_nodes():
    graph = Graph()
    a, b, c, d = (URIRef(f"urn:{name}") for name in "abcd")
    graph.add((a, URIRef("urn:p"), b))
    graph.add((c, URIRef("urn:p"), d))
    assert graph.all_nodes() == {a, b, c, d}
    assert graph.connected() is False
    graph.add((b, URIRef("urn:p"), c))
    assert graph.connected() is True
