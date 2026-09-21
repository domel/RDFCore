import pytest

from rdfcore import (
    Graph,
    Literal,
    TripleTerm,
    URIRef,
    required_rdf_version,
    validate_rdf_version,
    version_allows,
)
from rdfcore.interop import decode_direction_i18n, encode_direction_i18n


def test_version_validation_and_ordering():
    assert validate_rdf_version("auto") == "auto"
    assert version_allows("1.2-basic", "1.1")
    assert not version_allows("1.1", "1.2-basic")
    with pytest.raises(ValueError):
        validate_rdf_version("2.0")


def test_required_version_classifies_direction_and_nested_triple_terms():
    graph = Graph()
    graph.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x", lang="en", direction="ltr")))
    assert required_rdf_version(graph) == "1.2-basic"
    graph.add((URIRef("http://e/s"), URIRef("http://e/p2"), TripleTerm(URIRef("http://e/a"), URIRef("http://e/b"), Literal("c"))))
    assert required_rdf_version(graph) == "1.2"


def test_direction_i18n_interop_round_trip():
    source = Literal("مرحبا", lang="ar-EG", direction="rtl")
    encoded = encode_direction_i18n(source)
    assert encoded.datatype == URIRef("https://www.w3.org/ns/i18n#ar-eg_rtl")
    assert decode_direction_i18n(encoded) == source


def test_graph_entry_points_validate_rdf_version_argument():
    with pytest.raises(ValueError):
        Graph().parse(data="", format="turtle", rdf_version="2.0")
    with pytest.raises(ValueError):
        Graph().serialize(format="turtle", rdf_version="2.0")


def test_serializers_reject_rdf12_terms_instead_of_losing_them():
    graph = Graph().add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x", lang="en", direction="ltr")))
    with pytest.raises(ValueError, match="RDF 1.2 data requires"):
        graph.serialize(format="nt", rdf_version="1.1")
    with pytest.raises(ValueError, match="RDF 1.2 data requires"):
        graph.serialize(format="nt")
    encoded = graph.serialize(format="nt", rdf_version="1.1", downgrade="interop")
    assert "https://www.w3.org/ns/i18n#en_ltr" in encoded
    with pytest.raises(ValueError, match="downgrade"):
        Graph().serialize(format="nt", downgrade="unsafe")
