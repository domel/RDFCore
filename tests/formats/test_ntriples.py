import pytest

from rdfcore import Graph, Literal, NTParser, ParseError, ParserError, URIRef


def test_ntriples_parser_positive_cases():
    graph = Graph().parse(
        data='''
<http://example.org/s> <http://example.org/p> "line\\n"@EN .
<http://example.org/s> <http://example.org/n> "01"^^<http://www.w3.org/2001/XMLSchema#integer> .
''',
        format="nt",
    )
    values = list(graph.objects(URIRef("http://example.org/s"), None))
    assert Literal("line\n", lang="EN") in values
    assert any(str(value) == "01" and value.datatype == URIRef("http://www.w3.org/2001/XMLSchema#integer") for value in values)


def test_ntriples_parser_preserves_blank_node_identity():
    graph = Graph().parse(
        data='_:b <http://example.org/p> <http://example.org/o> .\n_:b <http://example.org/q> "x" .\n',
        format="ntriples",
    )
    assert len(list(graph.subjects(unique=True))) == 1


def test_ntriples_blank_node_labels_are_local_to_the_document():
    data = '_:b <http://example.org/p> <http://example.org/o> .\n'
    first = next(iter(Graph().parse(data=data, format="nt")))[0]
    second = next(iter(Graph().parse(data=data, format="nt")))[0]
    assert first != second
    assert ParseError is ParserError


def test_ntriples_parser_accepts_unicode_escapes_and_numeric_blank_nodes():
    graph = Graph().parse(
        data='<http://example.org/\\u0073> <http://example.org/p> _:1 .\n', format="nt"
    )
    assert list(graph) == [(URIRef("http://example.org/s"), URIRef("http://example.org/p"), graph.value())]


@pytest.mark.parametrize("data", [
    '<http://e/s> <http://e/p> "unterminated .\n',
    '<http://e/s> <http://e/p> "bad\\q" .\n',
    '<http://e/s> <http://e/p> <http://e/o>\n',
    '<http://e/s> <http://e/p> <http://e/o> garbage\n',
])
def test_ntriples_parser_reports_errors(data):
    with pytest.raises(ParserError, match="line 1"):
        Graph().parse(data=data, format="nt")


def test_ntriples_invalid_utf8_is_parser_error():
    with pytest.raises(ParserError, match="line 1"):
        Graph().parse(data=b"\xff", format="nt")


def test_ntriples_accepts_minimal_whitespace_and_trailing_comments():
    graph = Graph().parse(data='<http://e/s><http://e/p>"x".# comment\n', format="nt")
    assert len(graph) == 1
