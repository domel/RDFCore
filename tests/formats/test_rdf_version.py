import pytest

from rdfcore import (
    Graph,
    Literal,
    URIRef,
)
from rdfcore.interop import decode_direction_i18n, encode_direction_i18n


def test_direction_i18n_interop_round_trip():
    source = Literal("مرحبا", lang="ar-EG", direction="rtl")
    encoded = encode_direction_i18n(source)
    assert encoded.datatype == URIRef("https://www.w3.org/ns/i18n#ar-eg_rtl")
    assert decode_direction_i18n(encoded) == source


def test_serializers_reject_rdf12_terms_instead_of_losing_them():
    graph = Graph().add(
        (
            URIRef("http://e/s"),
            URIRef("http://e/p"),
            Literal("x", lang="en", direction="ltr"),
        )
    )
    with pytest.raises(ValueError, match="RDF 1.2 data requires"):
        graph.serialize(format="nt", rdf_version="1.1")
    with pytest.raises(ValueError, match="RDF 1.2 data requires"):
        graph.serialize(format="nt")
    encoded = graph.serialize(format="nt", rdf_version="1.1", downgrade="interop")
    assert "https://www.w3.org/ns/i18n#en_ltr" in encoded
    with pytest.raises(ValueError, match="downgrade"):
        Graph().serialize(format="nt", downgrade="unsafe")
