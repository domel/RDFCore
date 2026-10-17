"""N-Triples WD 2026-10-07 section 3; N-Quads WD 2026-10-10.

Canonical lexical syntax does not rename blank nodes or implement RDFC-1.0.
"""
import pytest

from rdfcore import Dataset, Graph, Literal, URIRef


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset)])
@pytest.mark.parametrize('character,escaped', [
    ('\x7f', r'\u007F'), ('\ufffe', r'\uFFFE'), ('\uffff', r'\uFFFF'),
    ('\x00', r'\u0000'), ('\x0b', r'\u000B'), ('\t', r'\t'),
    ('\x85', '\x85'), ('\U0001fffe', '\U0001fffe'),
])
def test_canonical_literal_escapes(format, cls, character, escaped):
    graph = cls().add((URIRef('urn:s'), URIRef('urn:p'), Literal(character)))
    assert graph.serialize(format=format, canonical=True) == (
        '<urn:s> <urn:p> "' + escaped + '" .\n')
