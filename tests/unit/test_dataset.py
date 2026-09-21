import pytest

from rdfcore import ConjunctiveGraph, DATASET_DEFAULT_GRAPH_ID, BNode, Dataset, URIRef


def test_dataset_default_and_named_graphs():
    dataset = Dataset()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    default_object = URIRef("http://example.org/default")
    named_object = URIRef("http://example.org/named")
    named = URIRef("http://example.org/graph")

    dataset.add((s, p, default_object))
    dataset.add((s, p, named_object, named))
    assert len(dataset.default_graph) == 1
    assert list(dataset.graph(named)) == [(s, p, named_object)]
    assert list(dataset.quads((None, None, None, None))) == [
        (s, p, default_object, DATASET_DEFAULT_GRAPH_ID),
        (s, p, named_object, named),
    ]


def test_dataset_default_union_and_remove_graph():
    dataset = Dataset(default_union=True)
    triple = (URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o"))
    graph_name = BNode("g")
    dataset.add((*triple, graph_name))
    assert list(dataset) == [triple]
    dataset.remove_graph(graph_name)
    assert list(dataset) == []


def test_dataset_deprecated_apis_warn():
    dataset = Dataset()
    with pytest.warns(DeprecationWarning):
        assert dataset.default_context is dataset.default_graph
    with pytest.warns(DeprecationWarning):
        list(dataset.contexts())


def test_conjunctive_graph_keeps_dataset_default_graph_context():
    with pytest.warns(DeprecationWarning):
        graph = ConjunctiveGraph(identifier=URIRef("http://example.org/conjunctive"))
    triple = (URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o"))
    graph.add(triple)
    assert list(graph.quads((None, None, None, None))) == [(*triple, DATASET_DEFAULT_GRAPH_ID)]
