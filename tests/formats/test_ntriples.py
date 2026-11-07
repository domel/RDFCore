from rdfcore import BNode, Graph, URIRef


def test_ntriples_parser_accepts_unicode_escapes_and_numeric_blank_nodes():
    graph = Graph().parse(
        data="<http://example.org/\\u0073> <http://example.org/p> _:1 .\n", format="nt"
    )
    subject, predicate, obj = next(iter(graph))
    assert subject == URIRef("http://example.org/s")
    assert predicate == URIRef("http://example.org/p")
    assert isinstance(obj, BNode)
