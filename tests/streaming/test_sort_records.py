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


def test_invalid_sort_records_never_execute_pickle(tmp_path):
    import io
    import pickle
    import pytest

    marker = tmp_path / "executed"

    class Hostile:
        def __reduce__(self):
            return eval, (
                f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')",
            )

    hostile = pickle.dumps(Hostile())
    framed_hostile = b"RCR2" + len(hostile).to_bytes(8, "big") + hostile
    for payload in (
        b"not a run",
        b"RCR2",
        b"RCR2" + (2**63).to_bytes(8, "big"),
        hostile,
        framed_hostile,
    ):
        try:
            with pytest.raises(ValueError):
                sort._read_record(io.BytesIO(payload))
        finally:
            assert not marker.exists(), "Untrusted sort record executed Python code"
