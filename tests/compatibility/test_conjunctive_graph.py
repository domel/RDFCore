"""Executable ConjunctiveGraph contracts against RDFLib 7.6.0."""

import pytest
import rdflib
import rdfcore


def populated(module):
    graph = module.ConjunctiveGraph(identifier=module.URIRef("urn:default"))
    triple = tuple(module.URIRef("urn:" + part) for part in ("s", "p", "o"))
    graph.add(triple)
    graph.get_context(module.URIRef("urn:named")).add(triple)
    graph.get_context(module.BNode("other")).add((triple[2], triple[1], triple[0]))
    return graph, triple


def normalized(rows):
    return sorted(
        tuple(
            (type(x).__name__, str(x.identifier if hasattr(x, "identifier") else x))
            for x in row
        )
        for row in rows
    )


def test_choices_and_empty_contexts():
    results = []
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        view = graph.get_context(module.URIRef("urn:empty"))
        view.add(triple).remove(triple)
        results.append(
            (
                normalized((g,) for g in graph.contexts()),
                normalized(graph.triples_choices(([triple[0]], None, None))),
                normalized(
                    graph.triples_choices(
                        ([triple[0]], None, None), graph.default_context
                    )
                ),
            )
        )
    assert results[0] == results[1]


def test_inplace_add_with_anonymous_default_and_view_replacement():
    for module in (rdflib, rdfcore):
        graph = module.ConjunctiveGraph()
        triple = tuple(module.URIRef("urn:" + x) for x in "spo")
        graph += [triple]
        assert len(graph.default_context) == 0
        context = next(graph.quads())[3]
        assert type(context) is module.ConjunctiveGraph
        assert context.identifier == graph.identifier
        assert type(next(graph.contexts())) is module.ConjunctiveGraph
        view = graph.get_context(graph.identifier)
        view.addN([(*triple, view)])
        assert type(next(graph.quads())[3]) is module.Graph


def test_lifecycle():
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        assert graph.open("unused") is None
        assert graph.commit() is graph
        assert graph.rollback() is graph
        assert graph.destroy("unused") is graph
        assert triple in graph
        assert graph.close() is None


@pytest.mark.parametrize("sqlite", [False, True])
def test_store_parity_and_reopen(sqlite, tmp_path):
    expected, triple = populated(rdflib)
    path = tmp_path / "conjunctive.sqlite"
    store = rdfcore.SQLiteStore(path) if sqlite else rdfcore.store.Memory()
    graph = rdfcore.ConjunctiveGraph(
        store=store, identifier=rdfcore.URIRef("urn:default")
    )
    t = tuple(rdfcore.URIRef(str(x)) for x in triple)
    graph.add(t).add((*t, rdfcore.URIRef("urn:named")))
    graph.get_context(rdfcore.BNode("other")).add((t[2], t[1], t[0]))
    assert normalized(graph.quads()) == normalized(expected.quads())
    assert graph.commit() is graph
    assert graph.rollback() is graph
    if sqlite:
        graph.close()
        graph = rdfcore.ConjunctiveGraph(
            store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef("urn:default")
        )
        assert normalized(graph.quads()) == normalized(expected.quads())
        with pytest.raises(RuntimeError), graph.store.transaction():
            graph.remove((None, None, None))
            raise RuntimeError("rollback")
        assert normalized(graph.quads()) == normalized(expected.quads())
    graph.remove((*t, rdfcore.URIRef("urn:named")))
    expected.remove((*triple, rdflib.URIRef("urn:named")))
    assert normalized(graph.quads()) == normalized(expected.quads())
    assert graph.remove_context(rdfcore.URIRef("urn:default")) is None
    expected.remove_context(rdflib.URIRef("urn:default"))
    assert normalized(graph.quads()) == normalized(expected.quads())
    graph.close()
