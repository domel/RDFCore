"""Unicode line parsing observations against the pinned RDFLib oracle."""

from io import BytesIO

import pytest
import rdflib
import rdfcore
from rdfcore.streaming import BoundedReadStream, parse_stream


@pytest.mark.parametrize('format', ['nt', 'nquads'])
@pytest.mark.parametrize('value', ['', 'ż🙂', 'ż🙂' * 4096])
def test_unicode_literal_matches_reference(format, value):
    data = f'<urn:s> <urn:p> "{value}" .\n'
    reference = rdflib.Dataset().parse(data=data, format=format)
    expected = next(reference.objects(rdflib.URIRef('urn:s'), rdflib.URIRef('urn:p')))
    record, = parse_stream(BoundedReadStream(BytesIO(data.encode()), chunk_size=1), format)
    assert type(record[2]).__name__ == type(expected).__name__
    assert str(record[2]) == str(expected)
    assert record[2].datatype == (rdfcore.URIRef(str(expected.datatype)) if expected.datatype else None)
    assert record[2].language == expected.language
