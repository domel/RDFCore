"""Executable ConjunctiveGraph contracts against RDFLib 7.6.0."""

import warnings

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('identifier', [None, '', False, 0, 'urn:g', 'bnode'])
def test_constructor(identifier):
    observations = []
    for module in (rdflib, rdfcore):
        value = module.BNode('context') if identifier == 'bnode' else identifier
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            graph = module.ConjunctiveGraph(identifier=value, default_graph_base='urn:base')
            default = graph.default_context
        observations.append((
            type(graph.identifier).__name__, type(default.identifier).__name__,
            graph.identifier == default.identifier,
            str(graph.identifier) if value else None,
            graph.base, default.base, graph.default_union, graph.context_aware,
            graph.store is default.store,
            graph.namespace_manager is default.namespace_manager,
            [(type(w.message).__name__, str(w.message)) for w in recorded],
        ))
        graph.default_context = default
        assert graph.default_context is default
    assert observations[0] == observations[1]


def test_subclass_and_non_context_store():
    for module in (rdflib, rdfcore):
        class Derived(module.ConjunctiveGraph):
            pass
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            graph = Derived()
        assert recorded == []
        assert graph.default_context.store is graph.store
        with pytest.warns(DeprecationWarning), pytest.raises(AssertionError, match='context aware store'):
            module.ConjunctiveGraph(store=module.store.Store())


def test_dataset_default_identifier_is_unchanged():
    graph = rdfcore.Dataset()
    assert graph.default_graph.identifier == rdfcore.URIRef('urn:x-rdflib:default')
