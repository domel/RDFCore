from io import BytesIO, StringIO

from rdfcore import Dataset, Graph, URIRef
from rdfcore.pipeline import convert
from rdfcore.streaming import BoundedReadStream, DatasetSink, GraphSink, NTStreamingWriter, parse_stream


class RecordingSink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_parse_stream_delivers_statements_to_fake_sink():
    sink = RecordingSink()
    returned = parse_stream(StringIO('<urn:s> <urn:p> "o" .\n'), "nt", sink)
    assert returned is sink
    assert len(sink.statements) == 1


def test_parse_stream_can_be_consumed_as_an_iterator():
    statements = list(parse_stream(StringIO('<urn:s> <urn:p> "o" .\n'), format="nt"))
    assert len(statements) == 1


def test_graph_and_dataset_adapters_preserve_default_graph_semantics():
    graph = Graph()
    GraphSink(graph).add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
    assert len(graph) == 1

    dataset = Dataset()
    sink = DatasetSink(dataset)
    sink.add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
    sink.add((URIRef("urn:n"), URIRef("urn:p"), URIRef("urn:o"), URIRef("urn:g")))
    assert len(list(dataset.quads())) == 2
    assert len(list(dataset.quads((None, None, None, URIRef("urn:g"))))) == 1


def test_convert_uses_fake_backend_without_materializing_graph():
    sink = RecordingSink()
    result = convert(StringIO('<urn:s> <urn:p> "o" .\n'), "nt", "nt", sink=sink)
    assert result is sink
    assert len(sink.statements) == 1


def test_nt_streaming_writer_and_bounded_reader():
    output = StringIO()
    writer = NTStreamingWriter(output)
    writer.add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
    assert output.getvalue() == '<urn:s> <urn:p> <urn:o> .\n'

    bounded = BoundedReadStream(BytesIO(b"abcdef"), chunk_size=2)
    assert bounded.read(100) == b"ab"
    assert bounded.read(100) == b"cd"
    assert BoundedReadStream(BytesIO(b"one\ntwo\n"), chunk_size=2).readline() == b"one\n"


def test_nt_to_nt_convert_streams_directly_between_file_like_objects():
    source = BoundedReadStream(BytesIO(b'<urn:s> <urn:p> "o" .\n'), chunk_size=3)
    output = StringIO()
    result = convert(source, "nt", "nt", sink=NTStreamingWriter(output))
    assert result.stream is output
    assert output.getvalue() == '<urn:s> <urn:p> "o" .\n'


def test_convert_supports_documented_source_destination_signature():
    output = StringIO()
    convert(
        StringIO('<urn:s> <urn:p> "o" .\n'),
        output,
        input_format="nt",
        output_format="nt",
    )
    assert output.getvalue() == '<urn:s> <urn:p> "o" .\n'
