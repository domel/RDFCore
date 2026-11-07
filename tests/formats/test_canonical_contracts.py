"""NT/NQ WD 2026-10-23 §3; lexical layout is separate from RDFC-1.0."""

import pytest

from rdfcore import BNode, Dataset, Graph, Literal, RDF, RDFS, TripleTerm, URIRef
from rdfcore.compare import isomorphic


@pytest.mark.parametrize("format,cls", [("nt12", Graph), ("nq12", Dataset)])
def test_canonical_nested_statement_has_exact_utf8_bytes(format, cls):
    value = Literal("é\t\n\x00\x7f\ufffe", lang="EN", direction="rtl")
    term = TripleTerm(BNode("kept"), URIRef("urn:p"), value)
    graph = cls().add((URIRef("urn:s"), RDF.reifies, term))
    expected = (
        "<urn:s> <" + str(RDF.reifies) + "> <<( _:kept <urn:p> "
        '"é\\t\\n\\u0000\\u007F\\uFFFE"@en--rtl )>> .\n'
    ).encode("utf-8")
    assert graph.serialize(format=format, canonical=True, encoding="utf-8") == expected


@pytest.mark.parametrize(
    "format,cls",
    [("nt12", Graph), ("nq12", Dataset), ("turtle12", Graph), ("trig12", Dataset)],
)
def test_canonical_flag_does_not_rename_blank_nodes(format, cls):
    a, b = cls(), cls()
    a.add((BNode("first"), RDFS.label, Literal("v", lang="EN")))
    b.add((BNode("second"), RDFS.label, Literal("v", lang="EN")))
    assert isomorphic(a, b)
    assert a.serialize(format=format, canonical=True) != b.serialize(
        format=format, canonical=True
    )
