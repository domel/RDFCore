import pytest

from rdfcore import BNode, Graph, Literal, TripleTerm, URIRef
from rdfcore.exceptions import ParserError
from rdfcore.plugins.parsers.ntriples11 import NTParser
from rdfcore.plugins.parsers.ntriples12 import NT12Parser


def test_nt12_parses_version_direction_and_triple_terms():
    graph = Graph().parse(data='''
        VERSION "1.2"
        <http://e/s> <http://e/p> "hello"@en--ltr .
        <http://e/s> <http://e/q> <<( <http://e/a> <http://e/b> _:o )>> .
    ''', format="nt12")
    directed = graph.value(URIRef("http://e/s"), URIRef("http://e/p"))
    embedded = graph.value(URIRef("http://e/s"), URIRef("http://e/q"))
    assert directed.direction == "ltr"
    assert isinstance(embedded, TripleTerm)
    assert embedded.subject == URIRef("http://e/a")
    assert embedded.predicate == URIRef("http://e/b")
    assert isinstance(embedded.object, BNode)


def test_nt11_and_nt12_have_separate_plugin_modules():
    assert NTParser.rdf_version == "1.1"
    assert NT12Parser.rdf_version == "1.2"


def test_nt11_alias_rejects_rdf12_terms():
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> "x"@en--rtl .', format="nt11")
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> <<( <http://e/a> <http://e/b> <http://e/c> )>> .', format="nt11")
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> "x"@en--rtl .', format="nt")


def test_nt12_version_is_case_sensitive_and_short_quoted():
    with pytest.raises(ParserError):
        Graph().parse(data='version "1.2"\n<http://e/s> <http://e/p> "x" .', format="nt12")
    with pytest.raises(ParserError):
        Graph().parse(data='VERSION "1.3"\n<http://e/s> <http://e/p> "x" .', format="nt12")


def test_nt12_enforces_explicit_rdf_version_and_rejects_short_triple_syntax():
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> "x"@en--rtl .', format="nt12", rdf_version="1.1")
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> <<( <http://e/a> <http://e/b> <http://e/c> )>> .', format="nt12", rdf_version="1.2-basic")
    with pytest.raises(ParserError):
        Graph().parse(data='<http://e/s> <http://e/p> << <http://e/a> <http://e/b> <http://e/c> >> .', format="nt12")
