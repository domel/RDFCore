from rdfcore import Graph, Literal, TripleTerm, URIRef


def test_turtle12_serializer_writes_version_and_rdf12_terms():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x", lang="EN", direction="rtl")))
    graph.add((URIRef("http://e/s"), URIRef("http://e/q"), TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), URIRef("http://e/c"))))
    text = graph.serialize(format="turtle12")
    assert text.startswith('VERSION "1.2"\n')
    assert '"x"@EN--rtl' in text
    assert '<<( <http://e/a> <http://e/b> <http://e/c> )>>' in text


def test_turtle12_round_trip_and_canonical_version_policy():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x", lang="EN", direction="ltr")))
    text = graph.serialize(format="turtle12", canonical=True)
    assert not text.startswith("VERSION")
    assert '"x"@en--ltr' in text
    parsed = Graph().parse(data=text, format="turtle12")
    assert set(parsed) == set(graph)


def test_turtle11_serializer_does_not_replace_turtle12_alias():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x")))
    assert graph.serialize(format="turtle11") == graph.serialize(format="turtle")
