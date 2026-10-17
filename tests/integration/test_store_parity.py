"""Shared graph observations against the pinned RDFLib executable oracle."""

import itertools

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('bound', list(itertools.product([False, True], repeat=3)))
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_store_queries_and_removal_match_rdflib(tmp_path, bound, backend):
    def exercise(module, store=None):
        kwargs = {} if store is None else {'store': store}
        graph = module.Graph(identifier=module.URIRef('urn:g'), **kwargs)
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        graph.add((s, p, module.Literal('text', lang='EN')))
        graph.add((s, p, module.Literal('text', lang='en')))
        graph.add((module.BNode('urn:s'), p, module.Literal('other')))
        target = (s, p, module.Literal('text', lang='en'))
        pattern = tuple(value if flag else None for value, flag in zip(target, bound))
        def records():
            return {(type(a).__name__, str(a), type(b).__name__, str(b),
                     type(c).__name__, str(c), c.language.lower() if c.language else None)
                    for a, b, c in graph.triples(pattern)}
        before = len(graph), records()
        graph.remove(pattern)
        after = len(graph), records()
        graph.close()
        return before, after
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore(tmp_path / 'parity.sqlite')
    assert exercise(rdfcore, store) == exercise(rdflib)


def test_sqlite_reopen_matches_language_identity(tmp_path):
    path = tmp_path / 'reopen.sqlite'
    graph = rdfcore.Graph(store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef('urn:g'))
    triple = (rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p'), rdfcore.Literal('text', lang='EN'))
    graph.add(triple)
    graph.close()
    reopened = rdfcore.Graph(store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef('urn:g'))
    equal_triple = (*triple[:2], rdfcore.Literal('text', lang='en'))
    assert equal_triple in reopened
    reopened.add(equal_triple)
    assert len(reopened) == 1
    reopened.remove(equal_triple)
    assert len(reopened) == 0
    reopened.close()
