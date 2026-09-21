from rdfcore import Graph, Literal, TripleTerm, URIRef


def test_nt12_serializer_writes_rdf12_terms_and_version():
    graph = Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("hello", lang="EN", direction="ltr")))
    graph.add((URIRef("http://e/s"), URIRef("http://e/q"), TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), URIRef("http://e/c"))))
    text = graph.serialize(format="nt12")
    assert text.startswith('VERSION "1.2"\n')
    assert '"hello"@EN--ltr' in text
    assert '<<( <http://e/a> <http://e/b> <http://e/c> )>>' in text


def test_nt12_canonical_omits_version_and_lowercases_language():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("hello", lang="EN", direction="rtl")))
    text = graph.serialize(format="nt12", canonical=True)
    assert not text.startswith("VERSION")
    assert '"hello"@en--rtl' in text


def test_nt12_round_trip():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("hello", lang="en", direction="ltr")))
    text = graph.serialize(format="nt12")
    parsed = Graph().parse(data=text, format="nt12")
    assert set(parsed) == set(graph)


def test_nt12_accepts_plain_rdf11_with_explicit_version():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x")))
    text = graph.serialize(format="nt12", rdf_version="1.1")
    assert not text.startswith("VERSION")
