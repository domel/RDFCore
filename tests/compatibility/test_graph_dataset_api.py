from rdfcore import Dataset


def test_dataset_graph_without_identifier_creates_named_graph():
    dataset = Dataset()
    graph = dataset.graph()
    assert graph is not dataset.default_graph
    assert graph.identifier != dataset.default_graph.identifier
