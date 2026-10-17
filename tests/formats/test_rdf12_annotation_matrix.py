import pytest

from rdfcore import Graph, RDF, TripleTerm, URIRef


@pytest.mark.parametrize('suffix,count', [
    ('{| :source :doc |}', 1),
    ('~ :first ~ :second', 2),
    ('~ :first {| :source :doc |} {| :source :other |}', 2),
])
def test_multiple_annotation_forms(suffix, count):
    graph = Graph().parse(data='PREFIX : <http://e/> :s :p :o '+suffix+' .', format='turtle12')
    assert len(list(graph.triples((None, RDF.reifies, None)))) == count
    assert (URIRef('http://e/s'), URIRef('http://e/p'), URIRef('http://e/o')) in graph


def test_explicit_reified_identifier():
    graph = Graph().parse(data='PREFIX : <http://e/> << :s :p :o ~ :id >> :q :z .', format='turtle12')
    assert (URIRef('http://e/id'), RDF.reifies, TripleTerm(URIRef('http://e/s'), URIRef('http://e/p'), URIRef('http://e/o'))) in graph


def test_turtle_terms_need_no_separating_whitespace():
    graph = Graph().parse(data='PREFIX : <http://e/> <urn:s>:p<<(<urn:a><urn:b><urn:c>)>>.', format='turtle12')
    assert isinstance(next(iter(graph))[2], TripleTerm)
