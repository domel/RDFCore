"""Independent expected graphs for Turtle/TriG RDF12 expansions."""

import pytest

from rdfcore import BNode, Dataset, Graph, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic


def iri(local):
    return URIRef("urn:" + local)


def expected(kind):
    if kind == "annotations":
        return [
            (iri("s"), iri("p"), iri("o")),
            (iri("r"), RDF.reifies, TripleTerm(iri("s"), iri("p"), iri("o"))),
            (iri("r"), iri("q"), iri("v")),
            (iri("nested"), RDF.reifies, TripleTerm(iri("r"), iri("q"), iri("v"))),
            (iri("nested"), iri("z"), iri("w")),
        ]
    a, b, c = BNode(), BNode(), BNode()
    return [
        (iri("s"), iri("list"), a),
        (a, RDF.first, iri("a")),
        (a, RDF.rest, b),
        (b, RDF.first, iri("b")),
        (b, RDF.rest, RDF.nil),
        (iri("s"), iri("prop"), c),
        (c, iri("q"), iri("v")),
    ]


@pytest.mark.parametrize("format,cls", [("turtle12", Graph), ("trig12", Dataset)])
@pytest.mark.parametrize("mode", ["pretty", "stream"])
@pytest.mark.parametrize(
    "kind,body",
    [
        ("annotations", ":s :p :o ~ :r {| :q :v ~ :nested {| :z :w |} |} ."),
        ("collections", ":s :list (:a :b) ; :prop [ :q :v ] ."),
    ],
)
def test_expansion_and_writers_preserve_exact_statements(format, cls, mode, kind, body):
    source = "PREFIX : <urn:> " + body
    target = cls()
    if cls is Dataset:
        source = (
            "PREFIX : <urn:> { " + body + " } :g { " + body + " } :g { :extra :p :o . }"
        )
        for triple in expected(kind):
            target.add(triple)
        for triple in expected(kind):
            target.graph(iri("g")).add(triple)
        target.graph(iri("g")).add((iri("extra"), iri("p"), iri("o")))
    else:
        for triple in expected(kind):
            target.add(triple)
    parsed = cls().parse(data=source, format=format)
    assert isomorphic(parsed, target)
    restored = cls().parse(
        data=parsed.serialize(format=format, mode=mode), format=format
    )
    assert isomorphic(restored, target)
