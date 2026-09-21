from io import BytesIO

from rdfcore import Literal, URIRef
from rdfcore.streaming import BoundedReadStream, parse_stream


class Sink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_turtle_streaming_parser_uses_sink_and_bounded_reads():
    source = BoundedReadStream(
        BytesIO(b'@prefix ex: <urn:> . ex:s ex:p "value" .\n'),
        chunk_size=2,
    )
    sink = Sink()
    assert parse_stream(source, "turtle", sink) is sink
    assert sink.statements == [(URIRef("urn:s"), URIRef("urn:p"), Literal("value", normalize=False))]


def test_turtle_streaming_parser_preserves_collections_and_property_lists():
    source = BytesIO(b'@prefix ex: <urn:> . ex:s ex:p [ ex:q ( ex:a ex:b ) ] .')
    sink = Sink()
    parse_stream(source, "turtle", sink)
    assert len(sink.statements) == 6
