from io import StringIO

import pytest

from rdfcore import Graph, Literal, TripleTerm, URIRef
from rdfcore.streaming import TurtleStreamingWriter, parse_stream


def test_turtle_streaming_writer_emits_statement_by_statement_and_round_trips():
    output = StringIO()
    writer = TurtleStreamingWriter(output)
    writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("x")))
    writer.add((URIRef("urn:t"), URIRef("urn:p"), URIRef("urn:o")))
    text = output.getvalue()
    assert text.count(".\n") == 2
    graph = Graph().parse(data=text, format="turtle")
    assert len(graph) == 2


def test_turtle12_streaming_writer_handles_triple_terms_and_direction():
    output = StringIO()
    writer = TurtleStreamingWriter(output)
    writer.add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), Literal("x", lang="en", direction="rtl"))))
    text = output.getvalue()
    assert text.startswith('VERSION "1.2"')
    graph = Graph().parse(data=text, format="turtle12")
    assert isinstance(next(iter(graph))[2], TripleTerm)


def test_streaming_turtle_writer_rejects_rdf12_in_rdf11_mode():
    writer = TurtleStreamingWriter(StringIO(), rdf_version="1.1")
    with pytest.raises(ValueError):
        writer.add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c"))))


def test_turtle_stream_writer_refuses_late_rdf12_profile_upgrade():
    writer = TurtleStreamingWriter(StringIO())
    writer.add((URIRef("urn:s"), URIRef("urn:p"), Literal("x", lang="en", direction="ltr")))
    with pytest.raises(ValueError, match="cannot upgrade"):
        writer.add((URIRef("urn:s"), URIRef("urn:p"), TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c"))))
