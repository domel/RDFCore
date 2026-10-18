"""Offline regressions for the five version cases added in W3C 42e6bb1.

Baseline: N-Triples WD 2026-10-07, grammar and version announcement.
https://www.w3.org/TR/2026/WD-rdf12-n-triples-20261007/#sec-grammar-grammar
Snapshot d5d930b03ee6b63b388d0bb28fdb29ee78a59ec0 includes one valid
announcement and four invalid forms. No upstream result is rewritten here.
"""

import pytest

from rdfcore import Graph, Literal, URIRef
from rdfcore.exceptions import ParserError


@pytest.mark.parametrize('format', ['nt12', 'application/n-triples; version=1.2'])
@pytest.mark.parametrize('announcement,valid', [
    ('VERSION "1.2"', True),
    ('version "1.2"', False),
    ('VERSION 1.2', False),
    ('VERSION <https://example.org/version-1.2>', False),
    ('@version "1.2" .', False),
])
def test_refreshed_version_cases(announcement, valid, format):
    data = announcement + '\n<urn:s> <urn:p> "Hello"@en--ltr .\n'
    if not valid:
        with pytest.raises(ParserError):
            Graph().parse(data=data, format=format)
        return
    graph = Graph().parse(data=data, format=format)
    assert set(graph) == {(URIRef('urn:s'), URIRef('urn:p'),
                           Literal('Hello', lang='en', direction='ltr'))}
