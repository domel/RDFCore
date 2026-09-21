import pytest

from rdfcore import BNode, Graph, Literal, RDF, URIRef


def test_items_reads_rdf_collection_and_detects_cycles():
    graph = Graph()
    head, tail = BNode("head"), BNode("tail")
    graph.add((head, RDF.first, Literal("one")))
    graph.add((head, RDF.rest, tail))
    graph.add((tail, RDF.first, Literal("two")))
    graph.add((tail, RDF.rest, RDF.nil))
    assert list(graph.items(head)) == [Literal("one"), Literal("two")]

    graph.set((tail, RDF.rest, head))
    with pytest.raises(ValueError, match="recursive"):
        list(graph.items(head))


def test_transitive_helpers_follow_cycles_once():
    graph = Graph()
    predicate = URIRef("urn:next")
    nodes = [URIRef(f"urn:{name}") for name in "abc"]
    for left, right in zip(nodes, nodes[1:] + nodes[:1]):
        graph.add((left, predicate, right))
    assert set(graph.transitive_objects(nodes[0], predicate)) == set(nodes)
    assert set(graph.transitive_subjects(predicate, nodes[0])) == set(nodes)
    assert set(graph.transitiveClosure(lambda node, g: g.objects(node, predicate), nodes[0])) == set(nodes)


def test_connected_and_all_nodes():
    graph = Graph()
    a, b, c, d = (URIRef(f"urn:{name}") for name in "abcd")
    graph.add((a, URIRef("urn:p"), b))
    graph.add((c, URIRef("urn:p"), d))
    assert graph.all_nodes() == {a, b, c, d}
    assert graph.connected() is False
    graph.add((b, URIRef("urn:p"), c))
    assert graph.connected() is True
