"""Resource cases, not a claim of constant memory for arbitrary terms.

NT12 nested terms: W3C RDF 1.2 N-Triples WD 2026-10-07, section 5.3.
"""

import gzip
from io import BytesIO

import pytest

from rdfcore import BNode, Literal, TripleTerm
from rdfcore.io import open_input
from rdfcore.streaming import BoundedReadStream, parse_stream


@pytest.mark.parametrize('format', ['nt', 'nquads', 'nt12'])
@pytest.mark.parametrize('compressed', [False, True])
def test_long_unicode_record_survives_one_byte_reads(format, compressed):
    value = 'ż🙂' * 4096
    data = f'<urn:s> <urn:p> "{value}" .\n'.encode()
    raw = BytesIO(gzip.compress(data) if compressed else data)
    source, _ = open_input(raw, compression='gz' if compressed else None, buffer_size=1)
    try:
        statements = list(parse_stream(BoundedReadStream(source, chunk_size=1), format))
        assert statements == [(statements[0][0], statements[0][1], Literal(value), None)]
    finally:
        source.close()


def test_many_blank_node_labels_keep_document_scope():
    data = ''.join(f'_:n{i} <urn:p> _:n0 .\n' for i in range(2000)).encode()
    records = list(parse_stream(BytesIO(data), 'nt'))
    assert len({record[0] for record in records}) == 2000
    assert isinstance(records[0][0], BNode)
    assert all(record[2] == records[0][0] for record in records)


def test_nested_terms_preserve_structure_with_one_byte_reads():
    term = '"value"@en--rtl'
    for _ in range(30):
        term = f'<<( <urn:s> <urn:p> {term} )>>'
    data = f'VERSION "1.2"\n<urn:s> <urn:p> {term} .\n'.encode()
    record, = parse_stream(BoundedReadStream(BytesIO(data), chunk_size=1), 'nt12')
    value = record[2]
    for _ in range(30):
        assert isinstance(value, TripleTerm)
        value = value.object
    assert value == Literal('value', lang='en', direction='rtl')
