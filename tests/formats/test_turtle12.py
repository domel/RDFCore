import pytest

from rdfcore import Graph, Literal, URIRef
from rdfcore.exceptions import BadSyntax
from rdfcore.plugins.parsers.turtle12 import Turtle12Parser


def test_turtle12_parses_version_and_directional_literal():
    graph = Graph().parse(data='VERSION "1.2-basic"\n@prefix : <http://e/> .\n:s :p "hello"@en--ltr .', format="turtle12")
    literal = graph.value(URIRef("http://e/s"), URIRef("http://e/p"))
    assert literal == Literal("hello", lang="en", direction="ltr")


def test_turtle12_supports_at_version_and_short_string_rules():
    graph = Graph().parse(data='@version \'1.2-basic\' . @prefix : <http://e/> . :s :p "x"@en--rtl .', format="turtle12")
    assert graph.value(URIRef("http://e/s"), URIRef("http://e/p")).direction == "rtl"
    assert len(Graph().parse(data='version "1.2-basic" @prefix : <http://e/> . :s :p "x"@en--ltr .', format="turtle12")) == 1
    with pytest.raises(BadSyntax):
        Graph().parse(data='@version """1.2-basic""" . :s :p "x" .', format="turtle12")


def test_turtle11_rejects_direction_and_turtle12_is_separate_module():
    with pytest.raises(BadSyntax):
        Graph().parse(data='@prefix : <http://e/> . :s :p "x"@en--ltr .', format="turtle")
    with pytest.raises(BadSyntax):
        Graph().parse(data='VERSION "1.2-basic"\n:s :p "x" .', format="turtle")
    assert Turtle12Parser.rdf_version == "1.2"


def test_turtle12_respects_explicit_rdf_version_limit():
    with pytest.raises(BadSyntax):
        Graph().parse(data='@prefix : <http://e/> . :s :p "x"@en--ltr .', format="turtle12", rdf_version="1.1")
