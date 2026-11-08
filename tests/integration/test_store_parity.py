"""Shared graph observations against the pinned RDFLib executable oracle."""

import itertools

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize("bound", list(itertools.product([False, True], repeat=3)))
@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_store_queries_and_removal_match_rdflib(tmp_path, bound, backend):
    def exercise(module, store=None):
        kwargs = {} if store is None else {"store": store}
        graph = module.Graph(identifier=module.URIRef("urn:g"), **kwargs)
        s, p = module.URIRef("urn:s"), module.URIRef("urn:p")
        graph.add((s, p, module.Literal("text", lang="EN")))
        graph.add((s, p, module.Literal("text", lang="en")))
        graph.add((module.BNode("urn:s"), p, module.Literal("other")))
        target = (s, p, module.Literal("text", lang="en"))
        pattern = tuple(value if flag else None for value, flag in zip(target, bound))

        def records():
            return {
                (
                    type(a).__name__,
                    str(a),
                    type(b).__name__,
                    str(b),
                    type(c).__name__,
                    str(c),
                    c.language.lower() if c.language else None,
                )
                for a, b, c in graph.triples(pattern)
            }

        before = len(graph), records()
        graph.remove(pattern)
        after = len(graph), records()
        graph.close()
        return before, after

    store = (
        rdfcore.Memory()
        if backend == "memory"
        else rdfcore.SQLiteStore(tmp_path / "parity.sqlite")
    )
    assert exercise(rdfcore, store) == exercise(rdflib)


def test_sqlite_reopen_matches_language_identity(tmp_path):
    path = tmp_path / "reopen.sqlite"
    graph = rdfcore.Graph(
        store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef("urn:g")
    )
    triple = (
        rdfcore.URIRef("urn:s"),
        rdfcore.URIRef("urn:p"),
        rdfcore.Literal("text", lang="EN"),
    )
    graph.add(triple)
    graph.close()
    reopened = rdfcore.Graph(
        store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef("urn:g")
    )
    equal_triple = (*triple[:2], rdfcore.Literal("text", lang="en"))
    assert equal_triple in reopened
    reopened.add(equal_triple)
    assert len(reopened) == 1
    reopened.remove(equal_triple)
    assert len(reopened) == 0
    reopened.close()


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('selection', ['default', 'named', 'union'])
def test_remove_unmatched_scalars_matches_rdflib(tmp_path, backend, selection):
    def exercise(module, store=None):
        dataset = module.Dataset(**({'store': store} if store is not None else {}))
        s, p, o, name = (module.URIRef('urn:' + x) for x in ('s', 'p', 'o', 'g'))
        triple = (s, p, o)
        def records():
            return sorted(tuple((type(t).__name__, str(t)) for t in row) for row in dataset.quads())
        try:
            for populated in (False, True):
                if populated:
                    dataset.add(triple).add(triple)
                    dataset.graph(name).add(triple)
                before = records()
                for value in ('other', 7, True, 1.5):
                    for slot in range(3):
                        pattern = [None, None, None]
                        pattern[slot] = value
                        if selection == 'union':
                            result = dataset.remove(tuple(pattern))
                            assert result is dataset
                        else:
                            graph = dataset.default_graph if selection == 'default' else dataset.graph(name)
                            assert graph.remove(tuple(pattern)) is graph
                        assert records() == before
            return records()
        finally:
            dataset.close()
    path = tmp_path / 'scalar-patterns.sqlite'
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore(path)
    assert exercise(rdfcore, store) == exercise(rdflib)
    if backend == 'sqlite':
        reopened = rdfcore.SQLiteStore(path)
        try:
            assert len(reopened) == 1
        finally:
            reopened.close()
