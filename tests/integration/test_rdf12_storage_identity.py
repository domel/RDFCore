"""RDF 1.2 Concepts 2026-04-07, sections 3.4 and 3.6.

Storage regression tests, not a claim of complete RDF 1.2 conformance.
"""

import pytest

from rdfcore import BNode, Dataset, Literal, Memory, SQLiteStore, TripleTerm, URIRef
from rdfcore.codec import encode


def equal_terms(kind):
    a = Literal('text', lang='EN', direction='rtl')
    b = Literal('text', lang='en', direction='rtl')
    if kind == 'nested':
        a = TripleTerm(BNode('x'), URIRef('urn:p'), TripleTerm(URIRef('urn:s'), URIRef('urn:p'), a))
        b = TripleTerm(BNode('x'), URIRef('urn:p'), TripleTerm(URIRef('urn:s'), URIRef('urn:p'), b))
    return a, b


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('kind', ['directional', 'nested'])
def test_rdf12_identity_and_reopen(tmp_path, backend, kind):
    path = tmp_path / 'rdf12.sqlite'
    store = Memory() if backend == 'memory' else SQLiteStore(path)
    dataset = Dataset(store=store)
    a, b = equal_terms(kind)
    assert a == b and hash(a) == hash(b)
    assert encode(a) == encode(b)
    ids = [dataset.default_graph.identifier, URIRef('urn:g1'), URIRef('urn:g2')]
    triple = URIRef('urn:s'), URIRef('urn:p'), a
    for identifier in ids:
        graph = dataset.graph(identifier)
        graph.add(triple)
        graph.add((*triple[:2], b))
        assert len(graph) == 1
    if backend == 'sqlite':
        dataset.close()
        dataset = Dataset(store=SQLiteStore(path))
    for identifier in ids:
        graph = dataset.graph(identifier)
        assert (*triple[:2], b) in graph
        graph.remove((*triple[:2], b))
        assert len(graph) == 0
    dataset.close()


def test_direction_and_nested_term_identity_is_immutable():
    literal, _ = equal_terms('directional')
    term, _ = equal_terms('nested')
    for value, attribute, replacement in [(literal, 'direction', 'ltr'), (term, 'object', literal)]:
        values = {value}
        original_hash = hash(value)
        with pytest.raises(AttributeError):
            setattr(value, attribute, replacement)
        with pytest.raises(AttributeError):
            delattr(value, attribute)
        assert value in values and hash(value) == original_hash
