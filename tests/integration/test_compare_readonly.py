"""Dataset exact comparison is an extension, not a graph-view mutation."""
import pytest
import rdflib
import rdfcore

from rdfcore.compare import isomorphic
from rdfcore.store import SQLiteStore


def test_graph_lookup_base_side_effect_remains_reference_compatible():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        graph = dataset.graph(module.URIRef('urn:g'), base='https://example.org/base/')
        assert graph.base == 'https://example.org/base/'
        assert dataset.graph(module.URIRef('urn:g')).base is None


def state(dataset):
    return (dataset.base, dataset.default_graph.base, dict(dataset._graphs),
            {key: graph.base for key, graph in dataset._graphs.items()},
            set(dataset.store.contexts()), list(dataset.namespace_manager.namespaces()))


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('outcome', ['equal', 'different', 'exception'])
@pytest.mark.parametrize('empty', [False, True])
def test_comparison_does_not_mutate_bases_registry_or_namespaces(tmp_path, monkeypatch, backend, outcome, empty):
    from rdfcore import Dataset, URIRef, Literal, BNode, TripleTerm
    from rdfcore import compare
    datasets = []
    try:
        for index in range(2):
            store = SQLiteStore(tmp_path / f'{index}.db') if backend == 'sqlite' else 'default'
            dataset = Dataset(store=store, default_graph_base=f'https://example.org/{index}/')
            graph = dataset.graph(URIRef('urn:g'), base=f'https://example.org/named/{index}/')
            dataset.graph(URIRef('urn:empty'), base='https://example.org/empty/')
            node = BNode(f'node{index}')
            dataset.graph(node, base='https://example.org/blank/')
            if not empty:
                graph.add((node, URIRef('urn:p'), TripleTerm(node, URIRef('urn:p'), Literal('v'))))
            if outcome == 'different' and index:
                dataset.graph(URIRef('urn:different'))
            datasets.append(dataset)
        original = [state(d) for d in datasets]
        if outcome == 'exception':
            def fail(*args): raise RuntimeError('comparison failure')
            monkeypatch.setattr(compare, '_match', fail)
            with pytest.raises(RuntimeError, match='comparison failure'):
                isomorphic(*datasets)
        else:
            assert isomorphic(*datasets) is (outcome == 'equal')
            assert isomorphic(*reversed(datasets)) is (outcome == 'equal')
        assert [state(d) for d in datasets] == original
    finally:
        for dataset in datasets:
            dataset.close()


def test_comparison_does_not_populate_reopened_dataset_graph_cache(tmp_path):
    from rdfcore import Dataset, URIRef
    path = tmp_path / 'dataset.db'
    store = SQLiteStore(path)
    original = Dataset(store=store)
    original.graph(URIRef('urn:empty'))
    original.close()
    reopened = Dataset(store=SQLiteStore(path))
    expected = Dataset()
    expected.graph(URIRef('urn:empty'))
    try:
        before = state(reopened)
        assert isomorphic(reopened, expected)
        assert state(reopened) == before
    finally:
        reopened.close()
