from io import StringIO

import pytest

from rdfcore import Dataset, Literal, TripleTerm, TriGStreamingWriter, URIRef


def test_trig_streaming_writer_switches_graph_blocks_without_dataset():
    output = StringIO()
    writer = TriGStreamingWriter(output)
    writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("default")))
    writer.add((URIRef("urn:n"), URIRef("urn:p"), Literal("named"), URIRef("urn:g")))
    writer.close()
    text = output.getvalue()
    assert text.count("{\n") == 2
    dataset = Dataset().parse(data=text, format="trig")
    assert len(list(dataset.quads())) == 2


def test_trig12_streaming_writer_preserves_triple_terms():
    output = StringIO()
    writer = TriGStreamingWriter(output, rdf_version="1.2")
    writer.add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c")), URIRef("urn:g")))
    writer.close()
    assert output.getvalue().startswith('VERSION "1.2"\n')
    dataset = Dataset().parse(data=output.getvalue(), format="trig12")
    assert isinstance(next(dataset.quads())[2], TripleTerm)


def test_trig_stream_writer_cannot_be_reopened_after_close():
    writer = TriGStreamingWriter(StringIO())
    writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("x")))
    writer.close()
    with pytest.raises(ValueError, match="after"):
        writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("y")))
