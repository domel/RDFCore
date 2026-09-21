from rdfcore import BNode, Graph, Literal, RDF, TripleTerm, URIRef
from rdfcore.interop import basic_decode, basic_encode


def test_basic_encode_and_decode_round_trip():
    graph = Graph()
    triple = TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), Literal("c"))
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), triple))
    encoded = basic_encode(graph)
    assert any(predicate == RDF.type and obj == RDF.PropositionForm for _, predicate, obj in encoded)
    decoded = basic_decode(encoded)
    assert set(decoded) == set(graph)


def test_basic_encode_handles_nested_triple_terms():
    inner = TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), Literal("c"))
    outer = TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), inner)
    graph = Graph().add((URIRef("http://e/x"), URIRef("http://e/y"), outer))
    assert set(basic_decode(basic_encode(graph))) == set(graph)


def test_serializer_interop_downgrade_encodes_triple_terms():
    triple = TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), Literal("c"))
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), triple))
    text = graph.serialize(format="nt", rdf_version="1.1", downgrade="interop")
    assert "PropositionForm" in text
    assert "<<(" not in text
