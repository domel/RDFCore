from io import StringIO

from rdfcore import Graph, Literal, Namespace, TurtleSerializer, URIRef


def test_turtle_serializer_prefixes_and_round_trip():
    graph = Graph()
    ex = Namespace("http://example.org/")
    graph.bind("ex", ex)
    graph.add((ex.s, ex.p, Literal("hello")))
    graph.add((ex.s, ex.link, ex.o))
    output = graph.serialize(format="turtle")
    assert "@prefix ex: <http://example.org/> ." in output
    assert "ex:s ex:link ex:o ." in output
    reparsed = Graph().parse(data=output, format="turtle")
    assert set(reparsed) == set(graph)


def test_turtle_serializer_uses_full_iri_and_destination():
    graph = Graph()
    triple = (URIRef("http://unknown.example/s"), URIRef("http://unknown.example/p"), Literal("x"))
    graph.add(triple)
    output = graph.serialize(format="ttl")
    assert "<http://unknown.example/s>" in output
    stream = StringIO()
    assert graph.serialize(stream, format="turtle") is graph
    assert stream.getvalue() == output
