from rdfcore import Dataset, Graph, Literal, URIRef


def test_graph_n3_uses_identifier_n3():
    graph = Graph(identifier=URIRef("urn:graph"))
    assert graph.n3() == "[<urn:graph>]"


def test_dataset_graph_compatibility_methods():
    dataset = Dataset()
    graph = dataset.get_context("urn:named")
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    graph.add(triple)

    assert dataset.get_graph("urn:named") is graph
    assert dataset.get_graph("urn:missing") is None
    assert dataset.add_graph("urn:other").identifier == URIRef("urn:other")
    assert dataset.context_id("urn:document") == URIRef("#context")
    assert dataset.context_id("urn:document#old", "#new") == URIRef("#new")


def test_dataset_graph_accepts_string_identifiers():
    dataset = Dataset()
    assert dataset.graph("urn:g").identifier == URIRef("urn:g")


def test_dataset_get_context_none_creates_blank_context():
    context = Dataset().get_context(None)
    assert context.identifier.__class__.__name__ == "BNode"


def test_dataset_graph_without_identifier_creates_named_graph():
    dataset = Dataset()
    graph = dataset.graph()
    assert graph is not dataset.default_graph
    assert graph.identifier != dataset.default_graph.identifier


def test_dataset_add_graph_copies_an_external_graph():
    source = Graph(identifier=URIRef("urn:copied"))
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    source.add(triple)
    target = Dataset().add_graph(source)
    assert target is not source
    assert triple in target
