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


def populated(module):
    graph = module.ConjunctiveGraph(identifier=module.URIRef('urn:default'))
    triple = tuple(module.URIRef('urn:' + part) for part in ('s', 'p', 'o'))
    graph.add(triple)
    graph.get_context(module.URIRef('urn:named')).add(triple)
    graph.get_context(module.BNode('other')).add((triple[2], triple[1], triple[0]))
    return graph, triple


def normalized(rows):
    return sorted(tuple((type(x).__name__, str(x.identifier if hasattr(x, 'identifier') else x))
                        for x in row) for row in rows)


@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('selector', ['all', 'default', 'named', 'graph', 'missing', 'none'])
def test_query_contracts(union, selector):
    results = []
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        graph.default_union = union
        context = {'all': None, 'none': None, 'default': graph.default_context,
                   'named': module.URIRef('urn:named'),
                   'graph': module.Graph(identifier=module.URIRef('urn:named')),
                   'missing': module.URIRef('urn:missing')}[selector]
        pattern = (None, None, None) if selector == 'all' else (None, None, None, context)
        results.append((normalized(graph.triples(pattern)), normalized(graph.quads(pattern)),
                        normalized(iter(graph)), len(graph), triple in graph,
                        (*triple, context) in graph,
                        normalized((g,) for g in graph.contexts()),
                        normalized((g,) for g in graph.contexts(triple)),
                        normalized(graph.triples(pattern, context=module.URIRef('urn:named')))))
        assert all(isinstance(row[3], module.Graph) for row in graph.quads())
    assert results[0] == results[1]


@pytest.mark.parametrize('quoted', [False, True])
def test_context_views(quoted):
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        view = graph.get_context('urn:named', quoted=quoted, base='urn:base')
        assert type(view) is module.Graph
        assert view.store is graph.store
        assert view.namespace_manager is graph.namespace_manager
        assert view.base == 'urn:base'
        assert triple in view
        assert graph.get_context('urn:named') is not view
        assert graph.get_graph(module.URIRef('urn:named')).identifier == view.identifier
        with pytest.raises(IndexError):
            graph.get_graph(module.URIRef('urn:absent'))
        assert graph.get_context('urn:empty').identifier not in {g.identifier for g in graph.contexts()}


def test_conjunctive_graph_is_not_a_dataset():
    for module in (rdflib, rdfcore):
        assert not isinstance(module.ConjunctiveGraph(), module.Dataset)


@pytest.mark.parametrize('value', [None, '', False, 0])
def test_falsey_contexts(value):
    for module in (rdflib, rdfcore):
        graph = module.ConjunctiveGraph()
        view = graph.get_context(value)
        assert isinstance(view.identifier, module.BNode)
        assert list(graph.contexts()) == []


def test_choices_and_empty_contexts():
    results = []
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        view = graph.get_context(module.URIRef('urn:empty'))
        view.add(triple).remove(triple)
        results.append((normalized((g,) for g in graph.contexts()),
                        normalized(graph.triples_choices(([triple[0]], None, None))),
                        normalized(graph.triples_choices(([triple[0]], None, None), graph.default_context))))
    assert results[0] == results[1]
