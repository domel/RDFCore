import pytest

from rdfcore import Dataset, Graph, Literal, URIRef
from rdfcore.exceptions import BadSyntax


def test_turtle_and_trig_accept_case_insensitive_sparql_directives():
    assert (
        len(
            Graph().parse(
                data="prefix ex: <http://example.org/> ex:s ex:p ex:o .",
                format="turtle",
            )
        )
        == 1
    )
    assert (
        len(
            Dataset().parse(
                data="base <http://example.org/> { <s> <p> <o> . }", format="trig"
            )
        )
        == 1
    )


def test_turtle_accepts_long_and_single_quoted_strings_and_requires_at_directive_dot():
    graph = Graph().parse(
        data='''
        @prefix ex: <http://example.org/> .
        ex:s ex:long """first
second""" ; ex:single 'it\\'s' .
    ''',
        format="turtle",
    )
    subject = URIRef("http://example.org/s")
    assert graph.value(subject, URIRef("http://example.org/long")) == Literal(
        "first\nsecond"
    )
    assert graph.value(subject, URIRef("http://example.org/single")) == Literal("it's")
    with pytest.raises(BadSyntax):
        Graph().parse(
            data="@prefix ex: <http://example.org/> ex:s ex:p ex:o .", format="turtle"
        )
