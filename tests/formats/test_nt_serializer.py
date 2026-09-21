from io import StringIO
from pathlib import Path

from rdfcore import Graph, Literal, NTSerializer, URIRef


def test_ntriples_serializer_round_trip_and_escaping():
    graph = Graph()
    subject = URIRef("http://example.org/s")
    predicate = URIRef("http://example.org/p")
    graph.add((subject, predicate, Literal('line\n"\t')))
    output = graph.serialize(format="nt")
    assert output == '<http://example.org/s> <http://example.org/p> "line\\n\\"\\t" .\n'
    reparsed = Graph().parse(data=output, format="nt")
    assert list(reparsed) == list(graph)


def test_ntriples_serializer_destination_and_encoding():
    graph = Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("ż")))
    stream = StringIO()
    assert graph.serialize(stream, format="nt") is graph
    assert "ż" in stream.getvalue()
    encoded = graph.serialize(format="nt", encoding="utf-8")
    assert isinstance(encoded, bytes)
    assert b"\xc5\xbc" in encoded


def test_ntriples_serializer_canonical_options():
    graph = Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x", lang="EN")))
    assert graph.serialize(format="nt", canonical=True).endswith('"x"@en .\n')


def test_ntriples_serializer_uses_valid_unicode_iri_escapes():
    graph = Graph()
    graph.add((URIRef("http://e/s%20space"), URIRef("http://e/p"), Literal("x")))
    output = graph.serialize(format="nt")
    assert "http://e/s%20space" in output
    assert list(Graph().parse(data=output, format="nt")) == list(graph)


def test_ntriples_path_round_trip(tmp_path: Path):
    path = tmp_path / "graph.nt"
    graph = Graph()
    triple = (URIRef("http://e/s"), URIRef("http://e/p"), Literal("ż"))
    graph.add(triple)
    assert graph.serialize(path, format="nt") is graph
    assert list(Graph().parse(path, format="nt")) == [triple]
