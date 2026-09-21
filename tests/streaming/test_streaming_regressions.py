import pytest
from io import StringIO

from rdfcore import Dataset, Graph, Literal, TripleTerm, URIRef
from rdfcore.streaming import TriGStreamingWriter, TurtleStreamingWriter


def test_graph_serialize_turtle_stream_mode_round_trips():
    graph = Graph().add((URIRef("urn:s"), URIRef("urn:p"), Literal("x")))
    text = graph.serialize(format="turtle", mode="stream")
    assert len(Graph().parse(data=text, format="turtle")) == 1


def test_dataset_serialize_trig12_stream_mode_preserves_graph_and_term():
    dataset = Dataset()
    dataset.add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c")), URIRef("urn:g")))
    text = dataset.serialize(format="trig12", mode="stream", rdf_version="1.2")
    parsed = Dataset().parse(data=text, format="trig12")
    assert isinstance(next(parsed.quads())[2], TripleTerm)


def test_unknown_serializer_mode_is_rejected():
    with pytest.raises(ValueError, match="mode"):
        Graph().serialize(format="turtle", mode="unknown")


def test_explicit_turtle12_stream_allows_rdf11_then_triple_term():
    output = StringIO()
    writer = TurtleStreamingWriter(output, rdf_version="1.2")
    writer.add((URIRef("urn:s1"), URIRef("urn:p"), Literal("plain")))
    writer.add((URIRef("urn:s2"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c"))))
    writer.close()
    assert output.getvalue().startswith('VERSION "1.2"\n')


def test_empty_trig_stream_writer_stays_closed():
    writer = TriGStreamingWriter(StringIO())
    writer.close()
    with pytest.raises(ValueError, match="after"):
        writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("x")))
