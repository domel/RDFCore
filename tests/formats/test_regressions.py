from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, Literal, URIRef
from rdfcore.exceptions import BadSyntax


def test_turtle_preserves_decimal_and_dotted_qname():
    graph = Graph().parse(data='''
        @prefix ex: <http://example.org/> .
        ex:s ex:property.name 1.25 .
    ''', format="turtle")
    assert graph.value(URIRef("http://example.org/s"), URIRef("http://example.org/property.name")) == Literal(
        "1.25", datatype="http://www.w3.org/2001/XMLSchema#decimal", normalize=False
    )


def test_turtle_parses_scientific_numeric_literal():
    graph = Graph().parse(data='@prefix ex: <http://e/> . ex:s ex:p 1E0 .', format="turtle")
    assert graph.value(URIRef("http://e/s"), URIRef("http://e/p")).datatype == URIRef("http://www.w3.org/2001/XMLSchema#double")


def test_turtle_and_trig_accept_case_insensitive_sparql_directives():
    assert len(Graph().parse(data="prefix ex: <http://example.org/> ex:s ex:p ex:o .", format="turtle")) == 1
    assert len(Dataset().parse(data="base <http://example.org/> { <s> <p> <o> . }", format="trig")) == 1


def test_turtle_accepts_long_and_single_quoted_strings_and_requires_at_directive_dot():
    graph = Graph().parse(data='''
        @prefix ex: <http://example.org/> .
        ex:s ex:long """first
second""" ; ex:single 'it\\'s' .
    ''', format="turtle")
    subject = URIRef("http://example.org/s")
    assert graph.value(subject, URIRef("http://example.org/long")) == Literal("first\nsecond")
    assert graph.value(subject, URIRef("http://example.org/single")) == Literal("it's")
    with pytest.raises(BadSyntax):
        Graph().parse(data="@prefix ex: <http://example.org/> ex:s ex:p ex:o .", format="turtle")


@pytest.mark.parametrize("format", ["nquads", "turtle", "trig"])
def test_serializers_write_to_binary_stream_with_default_encoding(format):
    graph = Dataset() if format in ("nquads", "trig") else Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x")))
    stream = BytesIO()
    assert graph.serialize(stream, format=format) is graph
    assert stream.getvalue()
