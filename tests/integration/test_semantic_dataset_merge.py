"""Semantics CRD 2026-09-24 §10, Definition of RDF dataset merge."""
import pytest

from rdfcore import BNode, Dataset, Graph, Literal, TripleTerm, URIRef
from rdfcore.semantics import merge_datasets

P, G = URIRef('urn:p'), URIRef('urn:g')


def test_merge_standardizes_apart_and_preserves_sharing_inside_each_dataset():
    inputs = [Dataset(), Dataset()]
    shared = BNode('shared')
    for dataset in inputs:
        dataset.default_graph.add((shared, P, Literal('default')))
        dataset.graph(G).add((shared, P, TripleTerm(shared, P, shared)))
        dataset.graph(shared).add((shared, P, Literal('named')))
    before = [set(d.quads()) for d in inputs]
    merged = merge_datasets(iter(inputs))
    nodes = set(merged.default_graph.subjects(P, Literal('default')))
    assert len(nodes) == 2 and all(isinstance(n, BNode) for n in nodes)
    assert shared not in nodes
    assert len(merged) == 6
    for node in nodes:
        assert (node, P, TripleTerm(node, P, node)) in merged.graph(G)
        assert (node, P, Literal('named')) in merged.graph(node)
    assert [set(d.quads()) for d in inputs] == before


def test_iri_named_graphs_merge_and_duplicate_ground_statements_deduplicate():
    inputs = [Dataset(), Dataset()]
    triple = (URIRef('urn:s'), P, Literal('v'))
    for d in inputs:
        d.graph(G).add(triple)
    merged = merge_datasets(inputs)
    assert set(merged.graph(G)) == {triple}
    assert len(merged) == 1
    assert not merged.default_graph


def test_default_graph_stays_separate_from_named_graphs():
    first, second = Dataset(), Dataset()
    triple = (URIRef('urn:s'), P, Literal('v'))
    first.default_graph.add(triple)
    second.graph(G).add(triple)
    merged = merge_datasets([first, second])
    assert set(merged.default_graph) == set(merged.graph(G)) == {triple}
    assert len(list(merged.quads())) == 2


def test_repeated_input_has_independent_blank_node_scopes():
    d = Dataset()
    d.default_graph.add((BNode('x'), P, Literal('v')))
    merged = merge_datasets([d, d])
    assert len(merged.default_graph) == 2


def test_merge_is_statement_label_based_and_does_not_invent_empty_graph_labels():
    d = Dataset()
    d.graph(G)
    merged = merge_datasets([d])
    assert {g.identifier for g in merged.graphs()} == {merged.default_graph.identifier}
    assert {g.identifier for g in d.graphs()} == {G, d.default_graph.identifier}
    assert len(merge_datasets([])) == 0


def test_merge_rejects_a_graph_without_changing_it():
    graph = Graph()
    graph.add((URIRef('urn:s'), P, Literal('v')))
    with pytest.raises(TypeError, match='Dataset'):
        merge_datasets([graph])
    assert len(graph) == 1


def test_budget_exhaustion_does_not_mutate_inputs():
    from rdfcore.semantics import EntailmentResourceLimit
    d = Dataset()
    d.default_graph.add((BNode('x'), P, Literal('v')))
    before = set(d.quads())
    with pytest.raises(EntailmentResourceLimit):
        merge_datasets([d], max_steps=0)
    assert set(d.quads()) == before


def test_generated_labels_cannot_collide_with_input_labels(monkeypatch):
    from types import SimpleNamespace
    from rdfcore import term
    d = Dataset()
    original = BNode('Ncollision')
    d.default_graph.add((original, P, Literal('v')))
    calls = 0

    def generated():
        nonlocal calls
        calls += 1
        return SimpleNamespace(hex='collision' if calls <= 5 else str(calls))

    monkeypatch.setattr(term, 'uuid4', generated)
    merged = merge_datasets([d])
    renamed = next(merged.default_graph.subjects())
    assert calls > 5
    assert isinstance(renamed, BNode) and renamed != original


def test_sqlite_inputs_remain_open_and_unchanged(tmp_path):
    from rdfcore import SQLiteStore
    store = SQLiteStore(tmp_path / 'merge.db')
    try:
        d = Dataset(store=store)
        d.graph(G).add((BNode('x'), P, Literal('v')))
        before = set(d.quads())
        merged = merge_datasets([d, d])
        assert len(merged.graph(G)) == 2
        assert set(d.quads()) == before
        d.default_graph.add((URIRef('urn:still-open'), P, Literal('v')))
        assert len(d.default_graph) == 1
    finally:
        store.close()
