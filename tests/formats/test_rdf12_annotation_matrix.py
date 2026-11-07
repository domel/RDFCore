from rdfcore import Graph, RDF, TripleTerm, URIRef


def test_explicit_reified_identifier():
    graph = Graph().parse(
        data="PREFIX : <http://e/> << :s :p :o ~ :id >> :q :z .", format="turtle12"
    )
    assert (
        URIRef("http://e/id"),
        RDF.reifies,
        TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o")),
    ) in graph
