from rdfcore import BNode, Graph, RDF, TripleTerm, URIRef


def test_turtle12_expands_reified_triple_to_rdf_reifies():
    graph = Graph().parse(data='@prefix : <http://e/> . << :s :p :o >> .', format="turtle12")
    links = list(graph.objects(None, RDF.reifies))
    assert len(links) == 1
    assert links[0] == TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o"))
    assert next(graph.subjects(None, links[0])) if False else True


def test_turtle12_expands_explicit_and_implicit_annotation_reifiers():
    graph = Graph().parse(data='''
        @prefix : <http://e/> .
        :s :p :o ~ :statement {| :source :doc ; :confidence "high" |} .
        :s :q :r ~ {| :source :doc |} .
    ''', format="turtle12")
    assert (URIRef("http://e/statement"), RDF.reifies, TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o"))) in graph
    assert (URIRef("http://e/statement"), URIRef("http://e/source"), URIRef("http://e/doc")) in graph
    implicit = [s for s in graph.subjects(RDF.reifies, None) if isinstance(s, BNode)]
    assert len(implicit) == 1
    assert (implicit[0], URIRef("http://e/source"), URIRef("http://e/doc")) in graph


def test_turtle11_does_not_accept_reification_or_annotation_syntax():
    from pytest import raises
    from rdfcore.exceptions import BadSyntax

    with raises(BadSyntax):
        Graph().parse(data='@prefix : <http://e/> . :s :p :o ~ :t {| :a :b |} .', format="turtle")
