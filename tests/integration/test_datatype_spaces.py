"""Finite witnesses do not constitute arbitrary value-space inclusion proofs."""

from rdfcore import Literal, RDF, XSD
from rdfcore.datatypes import datatype_value, SUPPORTED_DATATYPES
from rdfcore._datatype_spaces import contains


def test_membership_partition_covers_independent_boundaries_and_lexical_profiles():
    from rdfcore._datatype_spaces import membership_regions

    recognized = set(SUPPORTED_DATATYPES)
    regions = dict(membership_regions(recognized, step=lambda: None))
    candidates = [
        Literal(str(n), datatype=XSD.integer, normalize=False)
        for n in (
            -(10**50),
            -32769,
            -32768,
            -129,
            -128,
            -1,
            0,
            1,
            127,
            128,
            255,
            256,
            32767,
            32768,
            2**64 - 1,
            2**64,
            10**50,
        )
    ]
    candidates += [
        Literal(s, datatype=XSD.string, normalize=False)
        for s in (
            "",
            "two words",
            " leading",
            "trailing ",
            "\n",
            "\u0085",
            ":",
            "1name",
            "\u0300",
            "é",
            "en-123",
            "a_b",
        )
    ]
    candidates += [
        Literal("0.125", datatype=XSD.decimal),
        Literal("P2YT3S", datatype=XSD.duration),
        Literal("2000-02-29T12:00:00", datatype=XSD.dateTime),
        Literal("2000-02-29T12:00:00Z", datatype=XSD.dateTime),
        Literal('"\\u0000"', datatype=RDF.JSON),
    ]
    for sample in candidates:
        profile = frozenset(
            d for d in recognized if contains(datatype_value(sample), d)
        )
        assert profile in regions, repr(sample)
    for profile, witness in regions.items():
        assert profile == frozenset(
            d for d in recognized if contains(datatype_value(witness), d)
        )
