from io import BytesIO

from rdfcore import Dataset, Graph, Literal, URIRef
from rdfcore.streaming import BoundedReadStream


def test_graph_parse_uses_streaming_graph_sink():
    graph = Graph().parse(
        file=BoundedReadStream(BytesIO(b'<urn:s> <urn:p> "x" .\n'), chunk_size=1),
        format="nt",
    )
    assert graph.value(URIRef("urn:s"), URIRef("urn:p")) == Literal("x", normalize=False)


def test_dataset_parse_uses_streaming_dataset_sink_for_named_graphs():
    dataset = Dataset().parse(
        file=BoundedReadStream(BytesIO(b'<urn:s> <urn:p> "x" <urn:g> .\n'), chunk_size=1),
        format="nquads",
    )
    assert list(dataset.quads((None, None, None, URIRef("urn:g"))))
