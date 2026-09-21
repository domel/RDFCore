"""Small, dependency-optional differential matrix for the RDFLib 7.6 API.

The upstream package is a development/test dependency only.  These tests keep
the comparison focused on stable RDF 1.1 behavior and intentionally exclude
implementation-specific blank-node identifiers and serializer formatting.
"""

from __future__ import annotations

import pytest

rdflib = pytest.importorskip("rdflib")

from rdflib import BNode as UpstreamBNode
from rdflib import Dataset as UpstreamDataset
from rdflib import Graph as UpstreamGraph
from rdflib import Literal as UpstreamLiteral
from rdflib import URIRef as UpstreamURIRef

from rdfcore import BNode, Dataset, Graph, Literal, URIRef


def test_s19_term_api_matches_rdflib_for_stable_terms():
    cases = [
        (URIRef("http://example/s"), UpstreamURIRef("http://example/s")),
        (BNode("fixed"), UpstreamBNode("fixed")),
        (Literal("text"), UpstreamLiteral("text")),
        (Literal("1", datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer")),
         UpstreamLiteral("1", datatype=UpstreamURIRef("http://www.w3.org/2001/XMLSchema#integer"))),
        (Literal("hello", lang="en"), UpstreamLiteral("hello", lang="en")),
    ]
    for ours, upstream in cases:
        assert isinstance(ours, str)
        assert str(ours) == str(upstream)
        assert ours.n3() == upstream.n3()
        if isinstance(ours, Literal):
            assert ours.language == getattr(upstream, "language", None)
            assert str(ours.datatype or "") == str(getattr(upstream, "datatype", None) or "")
        else:
            assert ours == ours.__class__(str(ours))


def test_s19_graph_and_dataset_api_smoke_matrix():
    ours = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("o")))
    upstream = UpstreamGraph()
    upstream.add((UpstreamURIRef("http://e/s"), UpstreamURIRef("http://e/p"), UpstreamLiteral("o")))
    assert len(ours) == len(upstream) == 1
    assert str(ours.value(URIRef("http://e/s"), URIRef("http://e/p"))) == str(
        upstream.value(UpstreamURIRef("http://e/s"), UpstreamURIRef("http://e/p"))
    )

    ours_ds = Dataset()
    upstream_ds = UpstreamDataset()
    graph_id = URIRef("http://e/g")
    ours_ds.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("o"), graph_id))
    upstream_ds.add((UpstreamURIRef("http://e/s"), UpstreamURIRef("http://e/p"), UpstreamLiteral("o"), UpstreamURIRef(str(graph_id))))
    assert len(list(ours_ds.quads())) == len(list(upstream_ds.quads())) == 1


@pytest.mark.parametrize("format_name, document", [
    ("nt", '<http://e/s> <http://e/p> "o" .\n'),
    ("nquads", '<http://e/s> <http://e/p> "o" <http://e/g> .\n'),
    ("turtle", '@prefix e: <http://e/> . e:s e:p "o" .\n'),
    ("trig", '@prefix e: <http://e/> . e:g { e:s e:p "o" . }\n'),
])
def test_s19_four_rdf11_formats_match_upstream_graph_cardinality(format_name, document):
    ours = (Dataset() if format_name in ("nquads", "trig") else Graph()).parse(data=document, format=format_name)
    upstream = (UpstreamDataset() if format_name in ("nquads", "trig") else UpstreamGraph()).parse(data=document, format=format_name)
    if format_name in ("nquads", "trig"):
        assert len(list(ours.quads())) == len(list(upstream.quads()))
    else:
        assert len(ours) == len(upstream)


def test_s19_serializer_round_trip_is_semantically_stable():
    graph = Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("o")))
    for format_name in ("nt", "turtle"):
        encoded = graph.serialize(format=format_name)
        decoded = Graph().parse(data=encoded, format=format_name)
        assert set(decoded) == set(graph)
