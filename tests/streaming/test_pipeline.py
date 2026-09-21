from io import BytesIO, StringIO

import pytest

from rdfcore.pipeline import convert, count, validate
from rdfcore.streaming import FilterSink, MapSink


def test_count_and_validate_stream_without_graph():
    data = '<urn:s> <urn:p> "a" .\n<urn:t> <urn:p> "b" .\n'
    assert count(StringIO(data), "nt") == 2
    assert validate(StringIO(data), "nt") is True
    with pytest.raises(Exception):
        validate(StringIO('<urn:s> <urn:p> .\n'), "nt")


def test_filter_and_map_middleware():
    received = []
    mapped = MapSink(FilterSink(type("Sink", (), {"add": received.append})(), lambda t: t[0] == "urn:s"), lambda t: (t[0], t[1], "mapped"))
    mapped.add(("urn:s", "urn:p", "old"))
    mapped.add(("urn:t", "urn:p", "old"))
    assert received == [("urn:s", "urn:p", "mapped")]


def test_convert_nt_to_nquads_uses_default_graph():
    output = BytesIO()
    convert(BytesIO(b'<urn:s> <urn:p> "x" .\n'), output, input_format="nt", output_format="nquads")
    assert output.getvalue() == b'<urn:s> <urn:p> "x" .\n'
