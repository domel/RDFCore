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


@pytest.mark.parametrize('operation', ['add', 'addN', 'remove', 'set', 'iadd', 'isub'])
@pytest.mark.parametrize('context', ['none', 'named', 'foreign', 'default'])
def test_mutations(operation, context):
    results = []
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        target = {'none': None, 'named': module.URIRef('urn:named'),
                  'foreign': module.Graph(identifier=module.URIRef('urn:foreign')),
                  'default': graph.default_context}[context]
        if operation == 'add':
            result = graph.add((*triple, target))
        elif operation == 'addN':
            try:
                result = graph.addN([(*triple, target)])
            except Exception as exc:
                result = type(exc).__name__
        elif operation == 'remove':
            result = graph.remove((*triple, target))
        elif operation == 'set':
            result = graph.set((triple[0], triple[1], module.Literal('replacement')))
        elif operation == 'iadd':
            result = graph.__iadd__([triple])
        else:
            result = graph.__isub__([triple])
        results.append((result is graph, result if isinstance(result, str) else None,
                        normalized(graph.quads()), normalized(iter(graph)),
                        normalized((g,) for g in graph.contexts())))
        if context == 'foreign':
            assert len(target) == 0
    assert results[0] == results[1]


@pytest.mark.parametrize('value', ['plain', None, 'list', 'short'])
def test_invalid_add_and_partial_generator(value):
    results = []
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        invalid = {'plain': ('s', 'p', 'o'), None: (None, None, None),
                   'list': list(triple), 'short': triple[:2]}[value]
        try:
            graph.add(invalid)
            error = None
        except Exception as exc:
            error = type(exc).__name__
        def records():
            yield (*triple, module.URIRef('urn:first'))
            raise RuntimeError('stopped')
        with pytest.raises(RuntimeError, match='stopped'):
            graph.addN(records())
        results.append((error, normalized(graph.quads())))
    assert results[0] == results[1]


def test_lifecycle():
    for module in (rdflib, rdfcore):
        graph, triple = populated(module)
        assert graph.open('unused') is None
        assert graph.commit() is graph
        assert graph.rollback() is graph
        assert graph.destroy('unused') is graph
        assert triple in graph
        assert graph.close() is None


def test_store_delegation():
    for module in (rdflib, rdfcore):
        calls = []
        class RecordingStore(module.store.Store):
            context_aware = True

            def add(self, triple, context, quoted=False):
                calls.append(('add', context, quoted))

            def addN(self, quads):
                calls.extend(('addN', row[3]) for row in quads)

            def triples(self, triple, context=None):
                calls.append(('triples', context))
                return iter(())

            def open(self, configuration, create=False):
                calls.append(('open', configuration, create))
                return 17

            def close(self, commit_pending_transaction=False):
                calls.append(('close', commit_pending_transaction))
                return 17

        store = RecordingStore()
        graph = module.ConjunctiveGraph(store=store, identifier=module.URIRef('urn:d'))
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph.add(triple)
        assert calls[-1] == ('add', graph.default_context, False)
        graph.addN([(*triple, graph)])
        assert calls[-1] == ('addN', graph)
        list(graph.triples(triple, context=module.URIRef('urn:named')))
        assert calls[-1][1].identifier == module.URIRef('urn:named')
        list(graph.quads((*triple, module.URIRef('urn:named'))))
        assert calls[-1][1].identifier == module.URIRef('urn:named')
        assert graph.open('configuration', True) == 17
        assert graph.close(True) == 17
        assert calls[-2:] == [('open', 'configuration', True), ('close', True)]


@pytest.mark.parametrize('sqlite', [False, True])
def test_store_parity_and_reopen(sqlite, tmp_path):
    expected, triple = populated(rdflib)
    path = tmp_path / 'conjunctive.sqlite'
    store = rdfcore.SQLiteStore(path) if sqlite else rdfcore.store.Memory()
    graph = rdfcore.ConjunctiveGraph(store=store, identifier=rdfcore.URIRef('urn:default'))
    t = tuple(rdfcore.URIRef(str(x)) for x in triple)
    graph.add(t).add((*t, rdfcore.URIRef('urn:named')))
    graph.get_context(rdfcore.BNode('other')).add((t[2], t[1], t[0]))
    assert normalized(graph.quads()) == normalized(expected.quads())
    assert graph.commit() is graph
    assert graph.rollback() is graph
    if sqlite:
        graph.close()
        graph = rdfcore.ConjunctiveGraph(store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef('urn:default'))
        assert normalized(graph.quads()) == normalized(expected.quads())
        with pytest.raises(RuntimeError), graph.store.transaction():
            graph.remove((None, None, None))
            raise RuntimeError('rollback')
        assert normalized(graph.quads()) == normalized(expected.quads())
    graph.remove((*t, rdfcore.URIRef('urn:named')))
    expected.remove((*triple, rdflib.URIRef('urn:named')))
    assert normalized(graph.quads()) == normalized(expected.quads())
    assert graph.remove_context(rdfcore.URIRef('urn:default')) is None
    expected.remove_context(rdflib.URIRef('urn:default'))
    assert normalized(graph.quads()) == normalized(expected.quads())
    graph.close()
