import pytest

from rdfcore import Graph, TripleTerm, URIRef
from rdfcore.exceptions import BadSyntax


def test_turtle12_parses_triple_terms_and_nested_objects():
    graph = Graph().parse(data='''
        @prefix : <http://e/> .
        :s :p <<( :a :b :c )>> .
        :s :q <<( :a :b <<( :c :d :e )>> )>> .
    ''', format="turtle12")
    first = graph.value(URIRef("http://e/s"), URIRef("http://e/p"))
    second = graph.value(URIRef("http://e/s"), URIRef("http://e/q"))
    assert isinstance(first, TripleTerm)
    assert isinstance(second.object, TripleTerm)
    assert second.object.object == URIRef("http://e/e")


def test_turtle12_rejects_triple_terms_as_subject_or_predicate():
    with pytest.raises(BadSyntax):
        Graph().parse(data='<<( :a :b :c )>> <http://e/p> <http://e/o> .', format="turtle12")
    with pytest.raises(BadSyntax):
        Graph().parse(data='<http://e/s> <<( :a :b :c )>> <http://e/o> .', format="turtle12")


def test_turtle11_does_not_gain_triple_term_syntax():
    with pytest.raises(BadSyntax):
        Graph().parse(data='<http://e/s> <http://e/p> <<( <http://e/a> <http://e/b> <http://e/c> )>> .', format="turtle")


def test_turtle12_basic_profile_rejects_triple_terms():
    with pytest.raises(BadSyntax):
        Graph().parse(data='<http://e/s> <http://e/p> <<( <http://e/a> <http://e/b> <http://e/c> )>> .', format="turtle12", rdf_version="1.2-basic")
