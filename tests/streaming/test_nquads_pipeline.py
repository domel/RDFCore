from io import StringIO

import pytest

from rdfcore import URIRef
from rdfcore.exceptions import ParserError
from rdfcore.pipeline import convert
from rdfcore.streaming import NQStreamingWriter, parse_stream


class RecordingSink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_nquads_parser_streams_default_and_named_graphs():
    sink = RecordingSink()
    parse_stream(
        StringIO('<urn:s> <urn:p> "default" .\n<urn:n> <urn:p> "named" <urn:g> .\n'),
        "nquads",
        sink,
    )
    assert len(sink.statements) == 2
    assert len(sink.statements[0]) == 3
    assert sink.statements[1][3] == URIRef("urn:g")


def test_nquads_writer_preserves_default_and_named_graphs():
    output = StringIO()
    writer = NQStreamingWriter(output)
    writer.add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
    writer.add((URIRef("urn:n"), URIRef("urn:p"), URIRef("urn:o"), URIRef("urn:g")))
    assert output.getvalue().splitlines() == [
        '<urn:s> <urn:p> <urn:o> .',
        '<urn:n> <urn:p> <urn:o> <urn:g> .',
    ]


def test_nquads_to_nt_dataset_policy():
    data = '<urn:n> <urn:p> "named" <urn:g> .\n'
    with pytest.raises(ParserError, match="named graph"):
        convert(StringIO(data), "nquads", "nt", sink=NQStreamingWriter(StringIO()))
    output = StringIO()
    convert(StringIO(data), "nquads", "nt", sink=NQStreamingWriter(output), dataset_policy="default")
    assert output.getvalue() == ""
    convert(StringIO(data), "nquads", "nt", sink=NQStreamingWriter(output), dataset_policy="union")
    assert output.getvalue() == '<urn:n> <urn:p> "named" .\n'
