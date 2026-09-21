import pytest

from rdfcore import BNode, DATASET_DEFAULT_GRAPH_ID, Dataset, NQuadsParser, ParserError, URIRef


def test_nquads_parser_default_and_named_graphs():
    dataset = Dataset().parse(
        data=(
            '<http://e/s> <http://e/p> <http://e/default> .\n'
            '<http://e/s> <http://e/p> <http://e/named> <http://e/g> .\n'
            '<http://e/s> <http://e/p> _:o _:g .\n'
        ),
        format="nquads",
    )
    quads = list(dataset.quads())
    assert (URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/default"), DATASET_DEFAULT_GRAPH_ID) in quads
    assert any(graph == URIRef("http://e/g") for _, _, _, graph in quads)
    assert any(isinstance(graph, BNode) for _, _, _, graph in quads)


def test_nquads_rejects_literal_graph_label_and_missing_dot():
    with pytest.raises(ParserError, match="line 1"):
        Dataset().parse(data='<http://e/s> <http://e/p> <http://e/o> "not-graph" .\n', format="nquads")
    with pytest.raises(ParserError, match="line 1"):
        Dataset().parse(data='<http://e/s> <http://e/p> <http://e/o> <http://e/g>\n', format="nquads")
