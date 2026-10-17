"""Executable RDFLib 7.6.0 contract for context removal and graph retention."""
from types import SimpleNamespace
import inspect

import pytest
import rdflib
import rdfcore


CASES = ['graph', 'iri', 'blank', 'string', 'empty_string', 'none', 'default', 'default_view',
         'missing', 'missing_graph', 'empty_graph', 'external_graph', 'dataset',
         'literal', 'variable', 'integer', 'false', 'list', 'dict', 'object', 'duck']


def exercise(module, kind, union, case, store=None):
    kwargs = {} if store is None else {'store': store}
    if kind == 'Dataset':
        dataset = module.Dataset(default_union=union, **kwargs)
        default = dataset.default_graph
        create = dataset.graph
    else:
        dataset = module.ConjunctiveGraph(identifier=module.URIRef('urn:x-rdflib:default'), **kwargs)
        default = dataset.default_context
        create = dataset.get_context
    g, h, blank = [create(identifier) for identifier in
                   (module.URIRef('urn:g'), module.URIRef('urn:h'), module.BNode('g'))]
    empty = create(module.URIRef('urn:empty'))
    s, p, o = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('shared')
    for graph in (g, h, blank):
        graph.add((s, p, o))
        graph.add((s, p, o))
    default.add((s, p, module.Literal('default')))
    external = module.Graph(identifier=g.identifier)
    external.add((s, p, module.Literal('external')))
    context = {
        'graph': g, 'iri': g.identifier, 'blank': blank.identifier, 'string': 'urn:g',
        'empty_string': '', 'none': None, 'default': default, 'missing': module.URIRef('urn:missing'),
        'default_view': dataset.get_graph(default.identifier) if kind == 'Dataset' else dataset.get_context(default.identifier),
        'missing_graph': module.Graph(identifier=module.URIRef('urn:missing')),
        'empty_graph': empty, 'external_graph': external, 'dataset': dataset,
        'literal': module.Literal('urn:g'), 'variable': module.Variable('urn:g'),
        'integer': 42, 'false': False, 'list': [], 'dict': {}, 'object': object(),
        'duck': SimpleNamespace(identifier=module.URIRef('urn:g')),
    }[case]
    outcomes = []
    for _ in range(2):
        try:
            result = dataset.remove_context(context=context)
            outcomes.append(('return', result is None))
        except Exception as error:
            outcomes.append(('error', type(error).__name__, str(error)))
    def records(graph):
        return sorted(tuple((type(term).__name__, str(term)) for term in triple) for triple in graph)
    def contexts(triple=None):
        values = dataset.graphs(triple) if kind == 'Dataset' else dataset.contexts(triple)
        return sorted((type(graph.identifier).__name__, str(graph.identifier)) for graph in values)
    before_readd = (len(dataset), records(default), records(g), records(h), records(blank),
                    contexts(), contexts((s, p, o)), contexts((None, None, None)), records(external))
    g.add((s, p, module.Literal('again')))
    after_readd = (len(dataset), records(g), contexts())
    return outcomes, before_readd, after_readd, dataset


@pytest.mark.parametrize('kind,union', [('Dataset', False), ('Dataset', True), ('ConjunctiveGraph', True)])
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('case', CASES)
def test_remove_context_matches_reference(tmp_path, kind, union, backend, case):
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore(tmp_path / 'contexts.sqlite')
    try:
        expected = exercise(rdflib, kind, union, case)
        actual = exercise(rdfcore, kind, union, case, store)
        assert actual[:3] == expected[:3]
        if backend == 'sqlite':
            graph_names = sorted(str(graph.identifier) for graph in actual[3].graphs())
            store.close()
            store = rdfcore.SQLiteStore(tmp_path / 'contexts.sqlite')
            reopened = rdfcore.Dataset(store=store)
            assert sorted(str(graph.identifier) for graph in reopened.graphs()) == graph_names
    finally:
        store.close()


def test_signature_and_graph_exposure_match_reference():
    for kind in ('Dataset', 'ConjunctiveGraph'):
        assert list(inspect.signature(getattr(rdfcore, kind).remove_context).parameters) == [
            'self', 'context']
        for module in (rdflib, rdfcore):
            graph = getattr(module, kind)()
            with pytest.raises(TypeError):
                graph.remove_context()
            with pytest.raises(TypeError):
                graph.remove_context(graph=None)
    assert not hasattr(rdfcore.Graph, 'remove_context')


@pytest.mark.parametrize('selector', ['none', 'missing', 'string', 'graph', 'bad'])
def test_empty_dataset_removal_matches_reference(selector):
    def observe(module):
        dataset = module.Dataset()
        context = {'none': None, 'missing': module.URIRef('urn:missing'), 'string': 'urn:missing',
                   'graph': module.Graph(identifier=module.URIRef('urn:missing')), 'bad': []}[selector]
        try:
            result = dataset.remove_context(context)
            outcome = ('return', result)
        except Exception as error:
            outcome = ('error', type(error).__name__, str(error))
        return outcome, len(dataset), sorted(str(graph.identifier) for graph in dataset.graphs())
    assert observe(rdfcore) == observe(rdflib)


def test_graph_aware_store_retains_empty_context_like_reference():
    from rdflib.plugins.stores.memory import Memory as ReferenceMemory
    for module, store in ((rdflib, ReferenceMemory()), (rdfcore, rdfcore.Memory()),
                          (rdfcore, rdfcore.SQLiteStore())):
        context = module.URIRef('urn:g')
        triple = tuple(map(module.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        try:
            store.add(triple, context)
            store.remove(triple, context)
            assert list(store.contexts()) == [context]
            assert list(store.contexts(triple)) == []
        finally:
            store.close()


def test_sqlite_remove_context_rolls_back_and_preserves_registration():
    store = rdfcore.SQLiteStore()
    try:
        dataset = rdfcore.Dataset(store=store)
        graph = dataset.graph(rdfcore.URIRef('urn:g'))
        triple = tuple(map(rdfcore.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        graph.add(triple)
        with pytest.raises(RuntimeError, match='rollback'):
            with store.transaction():
                assert dataset.remove_context(graph) is None
                assert len(graph) == 0
                raise RuntimeError('rollback')
        assert triple in graph
        assert graph.identifier in {g.identifier for g in dataset.graphs()}
        assert dataset.remove_context(graph) is None
        assert len(graph) == 0
        assert graph.identifier in {g.identifier for g in dataset.graphs()}
        assert dataset.remove_graph(graph) is dataset
        assert graph.identifier not in {g.identifier for g in dataset.graphs()}
    finally:
        store.close()


def test_remove_context_forwards_to_custom_store_without_coercion():
    from rdflib.plugins.stores.memory import Memory as ReferenceMemory
    for module, base in ((rdflib, ReferenceMemory), (rdfcore, rdfcore.Memory)):
        class RecordingStore(base):
            def remove(self, triple_pattern, context=None):
                self.recorded = triple_pattern, context
                return 42
        store = RecordingStore()
        dataset = module.Dataset(store=store)
        selector = object()
        assert dataset.remove_context(selector) is None
        assert store.recorded == ((None, None, None), selector)
        assert store.recorded[1] is selector


def test_existing_sqlite_database_gets_context_registry_without_term_changes(tmp_path):
    import sqlite3
    from rdfcore.codec import encode
    path = tmp_path / 'existing.sqlite'
    triple = tuple(map(rdfcore.URIRef, ('urn:s', 'urn:p', 'urn:o')))
    context = rdfcore.URIRef('urn:g')
    row = tuple(encode(term) for term in (*triple, context))
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE triples (s BLOB, p BLOB, o BLOB, context BLOB, PRIMARY KEY(s,p,o,context))')
        connection.execute('INSERT INTO triples VALUES (?,?,?,?)', row)
        connection.execute('PRAGMA user_version=1')
    store = rdfcore.SQLiteStore(path)
    try:
        dataset = rdfcore.Dataset(store=store)
        assert triple in dataset.graph(context)
        assert store._connection.execute('SELECT s,p,o,context FROM triples').fetchone() == row
        assert store._connection.execute('PRAGMA user_version').fetchone()[0] == 1
        dataset.remove_context(context)
    finally:
        store.close()
    store = rdfcore.SQLiteStore(path)
    try:
        dataset = rdfcore.Dataset(store=store)
        assert len(dataset) == 0
        assert context in {graph.identifier for graph in dataset.graphs()}
    finally:
        store.close()


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_removing_last_asserted_context_clears_union_copy(backend):
    def observe(module, store=None):
        dataset = module.Dataset(default_union=True, **({'store': store} if store is not None else {}))
        triple = tuple(map(module.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        unrelated = (*triple[:2], module.URIRef('urn:unrelated'))
        dataset.add((*triple, None))
        dataset.add((*unrelated, None))
        identifiers = [module.URIRef('urn:g'), module.URIRef('urn:h')]
        for identifier in identifiers:
            dataset.graph(identifier).add(triple)
        dataset.get_context(module.URIRef('urn:missing')).remove(triple)
        assert len(dataset) == 2
        result = []
        for identifier in identifiers:
            assert dataset.remove_context(identifier) is None
            result.append((len(dataset), sorted(tuple(map(str, t)) for t in dataset.triples((None, None, None)))))
        return result
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore()
    try:
        assert observe(rdfcore, store) == observe(rdflib)
    finally:
        store.close()


def test_sqlite_registers_cached_graph_after_creation_rollback():
    store = rdfcore.SQLiteStore()
    try:
        dataset = rdfcore.Dataset(store=store)
        identifier = rdfcore.URIRef('urn:rolled-back')
        with pytest.raises(RuntimeError):
            with store.transaction():
                dataset.graph(identifier)
                raise RuntimeError('rollback')
        assert identifier not in set(store.contexts())
        dataset.graph(identifier)
        dataset.remove_context(identifier)
        assert identifier in set(store.contexts())
    finally:
        store.close()


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_dataset_as_context_selects_own_identifier_not_default_graph(backend):
    def observe(module, store=None):
        dataset = module.Dataset(**({'store': store} if store is not None else {}))
        assert isinstance(dataset.identifier, module.BNode)
        assert dataset.identifier != dataset.default_graph.identifier
        triple = tuple(map(module.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        dataset.add(triple)
        own = dataset.graph(dataset.identifier)
        own.add((*triple[:2], module.URIRef('urn:own')))
        assert dataset.remove_context(dataset) is None
        return len(dataset), len(dataset.default_graph), len(own)
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore()
    try:
        assert observe(rdfcore, store) == observe(rdflib)
    finally:
        store.close()


@pytest.mark.parametrize('identifier', [None, 'urn:custom', '', 'blank', 'empty_blank'])
@pytest.mark.parametrize('selector', ['self', 'default', 'default_identifier'])
def test_conjunctive_context_identity_matches_reference(identifier, selector):
    def observe(module):
        value = module.BNode('named') if identifier == 'blank' else module.BNode('') if identifier == 'empty_blank' else identifier
        graph = module.ConjunctiveGraph(identifier=value)
        default = graph.default_context
        triple = tuple(map(module.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        graph.add(triple)
        context = {'self': graph, 'default': default, 'default_identifier': default.identifier}[selector]
        assert graph.remove_context(context) is None
        return (type(graph.identifier).__name__, type(default.identifier).__name__,
                graph.identifier == default.identifier, len(graph), len(default))
    assert observe(rdfcore) == observe(rdflib)
