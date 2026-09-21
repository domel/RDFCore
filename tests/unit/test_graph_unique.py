from rdfcore import Graph, URIRef


def test_iterator_unique_flag_controls_deduplication():
    graph = Graph()
    subject = URIRef("http://e/s")
    predicate = URIRef("http://e/p")
    graph.add((subject, predicate, URIRef("http://e/o1")))
    graph.add((subject, URIRef("http://e/p2"), URIRef("http://e/o2")))
    assert list(graph.subjects()) == [subject, subject]
    assert list(graph.subjects(unique=True)) == [subject]
