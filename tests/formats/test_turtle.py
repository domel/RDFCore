import pytest

from rdfcore import Graph, Literal, RDF, URIRef
from rdfcore.exceptions import BadSyntax


def test_turtle_parser_prefixes_literals_and_lists():
    graph = Graph().parse(data='''
        @prefix ex: <http://example.org/> .
        ex:s ex:p "text" ; ex:n 01 ; ex:list ( ex:a ex:b ) .
    ''', format="turtle")
    s = URIRef("http://example.org/s")
    assert Literal("text") in list(graph.objects(s, URIRef("http://example.org/p")))
    assert Literal("01", datatype="http://www.w3.org/2001/XMLSchema#integer", normalize=False) in list(graph.objects(s, URIRef("http://example.org/n")))
    head = graph.value(s, URIRef("http://example.org/list"))
    assert graph.value(head, RDF.first) == URIRef("http://example.org/a")


def test_turtle_parser_base_and_blank_node_property_list():
    graph = Graph().parse(data='''
        @base <http://example.org/base/> .
        <s> <p> [ <q> "x" ] .
    ''', format="ttl")
    subject = URIRef("http://example.org/base/s")
    blank = graph.value(subject, URIRef("http://example.org/base/p"))
    assert graph.value(blank, URIRef("http://example.org/base/q")) == Literal("x")


def test_turtle_parser_rejects_unknown_prefix():
    with pytest.raises(BadSyntax):
        Graph().parse(data="ex:s ex:p ex:o .", format="turtle")
