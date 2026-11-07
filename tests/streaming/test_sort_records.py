"""Temporary sort files are data, never executable pickle."""

import importlib

from rdfcore import Literal, URIRef, external_sort

sort = importlib.import_module("rdfcore.external_sort")


def test_sort_preserves_literal_native_values_and_flags():
    from rdfcore import XSD

    values = [
        Literal(1),
        Literal(True),
        Literal("P1D", datatype=XSD.duration) - Literal("P1M", datatype=XSD.duration),
    ]
    for value in values:
        restored = list(
            external_sort([(URIRef("urn:s"), URIRef("urn:p"), value)], memory_budget=1)
        )[0][2]
        assert restored.ill_typed is value.ill_typed
        assert type(restored.value) is type(value.value)
        assert restored.value == value.value
