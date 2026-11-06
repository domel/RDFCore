"""Graph/Dataset acceptance matrix, independently executed on each backend."""
import pytest
import rdflib
import rdfcore


def term(value):
    if isinstance(value, tuple):
        return tuple(term(item) for item in value)
    return type(value).__name__, str(value), str(getattr(value, 'datatype', None)), getattr(value, 'language', None)


@pytest.mark.parametrize('kind', ['Graph', 'Dataset'])
@pytest.mark.parametrize('sqlite', [False, True])
@pytest.mark.parametrize('case', ['list-add', 'bad-subject', 'literal-subject', 'variable',
                                  'none-subject-set', 'none-predicate-set', 'bad-object-set',
                                  'empty-list-subjects', 'list-subjects', 'bulk-none', 'bulk-failure',
                                  'remove-missing', 'choices', 'slice', 'repeat', 'unscoped-remove'])
def test_shared_graph_operations(kind, sqlite, case):
    observations = []
    for module in (rdflib, rdfcore):
        options = {'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}
        graph = getattr(module, kind)(**options)
        s, p, o = [module.URIRef('urn:' + x) for x in 'spo']
        graph.add((s, p, o))
        try:
            if case == 'list-add':
                result = graph.add([o, p, s])
            elif case == 'bad-subject':
                result = graph.add((None, p, o))
            elif case == 'literal-subject':
                result = graph.add((module.Literal('s'), p, o))
            elif case == 'variable':
                result = graph.add((module.Variable('s'), p, o))
            elif case == 'none-subject-set':
                result = graph.set((None, p, o))
            elif case == 'none-predicate-set':
                result = graph.set((s, None, o))
            elif case == 'bad-object-set':
                result = graph.set((s, p, None))
            elif case in ('empty-list-subjects', 'list-subjects'):
                result = sorted(map(term, graph.subjects(p, [] if case.startswith('empty') else [o, o], unique=True)))
            elif case == 'bulk-none':
                result = graph.addN([(*[s, p, o], None)])
            elif case == 'bulk-failure':
                def rows():
                    yield o, p, s, graph
                    raise RuntimeError('stop')
                result = graph.addN(rows())
            elif case == 'remove-missing':
                result = graph.remove((o, p, None))
            elif case == 'choices':
                result = sorted(map(term, graph.triples_choices(([s, s], p, None))))
            elif case == 'slice':
                result = sorted(map(term, graph[s:p]))
            elif case == 'repeat':
                result = sorted(map(term, graph.objects(s, p))) == sorted(map(term, graph.objects(s, p)))
            elif case == 'unscoped-remove':
                if kind == 'Dataset':
                    graph.add((o, p, s, None))
                    result = graph.remove((None, None, None, None))
                else:
                    result = graph.remove((None, None, None))
            outcome = ('self',) if result is graph else ('result', result)
        except Exception as error:
            outcome = ('error', type(error).__name__)
        # Check concrete graph data, preserving term kinds and literal metadata.
        rows = graph.triples((None, None, None))
        observations.append((outcome, len(graph), sorted(map(term, rows))))
        graph.close()
    assert observations[0] == observations[1]


def test_explicit_rdf_validation_preserves_strict_model_checks():
    s, p = rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p')
    for invalid in [(None, p, s), (rdfcore.Literal('s'), p, s), (rdfcore.Variable('s'), p, s)]:
        with pytest.raises(TypeError):
            rdfcore.Graph().add(invalid, validate=True)


def test_add_only_consumes_required_iterator_prefix():
    for module in (rdflib, rdfcore):
        observed = []
        def terms():
            for value in range(10):
                observed.append(value)
                yield module.URIRef('urn:' + str(value))
        with pytest.raises(ValueError):
            module.Graph().add(terms())
        assert observed == [0, 1, 2, 3]


def test_graph_delegates_graph_contexts_to_custom_store():
    for module in (rdflib, rdfcore):
        calls = []
        class Custom(module.store.Store):
            def add(self, triple, context, quoted=False): calls.append(('add', context))
            def addN(self, quads): calls.extend(('addN', row[3]) for row in quads)
            def remove(self, triple, context=None): calls.append(('remove', context))
            def triples(self, pattern, context=None):
                calls.append(('triples', context))
                return iter(())
            def __len__(self, context=None):
                calls.append(('len', context))
                return 0
        graph = module.Graph(store=Custom())
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph.add(triple)
        graph.addN([(*triple, graph)])
        graph.remove(triple)
        list(graph.triples(triple))
        len(graph)
        assert [row[0] for row in calls] == ['add', 'addN', 'remove', 'triples', 'len']
        assert all(row[1] is graph for row in calls)


@pytest.mark.parametrize('mode', ['rdflib', 'core', 'none', 'cc', 'bad', None, False])
def test_default_namespace_sets(mode):
    results = []
    for module in (rdflib, rdfcore):
        try:
            graph = module.Graph(bind_namespaces=mode)
            results.append([(p, str(uri)) for p, uri in graph.namespaces()])
        except Exception as error:
            results.append(type(error).__name__)
    assert results[0] == results[1]


def test_namespace_manager_store_is_a_property():
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        assert graph.namespace_manager.store is graph.store


@pytest.mark.parametrize('sqlite', [False, True])
@pytest.mark.parametrize('case', ['literal', 'variable', 'step-zero', 'step-false', 'step-one', 'empty', 'bad'])
def test_resource_indexing_edges(sqlite, case):
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(**({'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}))
        s, p, o = [module.URIRef('urn:' + x) for x in 'spo']
        graph.add((s, p, o))
        resource = graph.resource(s)
        selector = {'literal': module.Literal('p'), 'variable': module.Variable('p'),
                    'step-zero': slice(p, None, 0), 'step-false': slice(p, None, False),
                    'step-one': slice(p, None, 1), 'empty': slice(None, None), 'bad': 1}[case]
        try:
            value = resource[selector]
            results.append(('value', sorted((type(x).__name__, str(x.identifier)) if hasattr(x, 'identifier')
                                           else term(x) for x in value)))
        except Exception as error:
            results.append(('error', type(error).__name__))
        graph.close()
    assert results[0] == results[1]


@pytest.mark.parametrize('sqlite', [False, True])
@pytest.mark.parametrize('size', [0, 1, 3])
@pytest.mark.parametrize('operation', ['get', 'set', 'delete', 'append', 'iadd', 'clear', 'n3', 'iterate', 'invalid-iadd'])
def test_collection_store_matrix(sqlite, size, operation):
    from .test_collection_matrix import observe
    store = rdfcore.SQLiteStore() if sqlite else rdfcore.Memory()
    try:
        assert observe(rdfcore, size, operation, store=store) == observe(rdflib, size, operation)
    finally:
        store.close()


@pytest.mark.parametrize('sqlite', [False, True])
@pytest.mark.parametrize('empty', [False, True])
@pytest.mark.parametrize('operation', ['transitive_objects', 'transitive_subjects', 'transitiveClosure',
                                     'connected', 'all_nodes', 'items', 'namespace', 'resource'])
def test_traversal_and_wrappers(sqlite, empty, operation):
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(identifier=module.URIRef('urn:g'), **({'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}))
        a, b, c, p = [module.URIRef('urn:' + x) for x in 'abcp']
        if not empty:
            graph.add((a, p, b)).add((b, p, c)).add((c, p, a))
        try:
            if operation == 'transitive_objects':
                remember = {}
                value = tuple(map(term, graph.transitive_objects(a, p, remember)))
                value = value, sorted((term(node), count) for node, count in remember.items())
            elif operation == 'transitive_subjects':
                value = tuple(map(term, graph.transitive_subjects(p, a)))
            elif operation == 'transitiveClosure':
                value = tuple(map(term, graph.transitiveClosure(lambda node, g: g.objects(node, p), a)))
            elif operation == 'connected':
                value = graph.connected()
            elif operation == 'all_nodes':
                value = sorted(map(term, graph.all_nodes()))
            elif operation == 'items':
                head = module.URIRef('urn:list')
                if not empty:
                    graph.add((head, module.RDF.first, a)).add((head, module.RDF.rest, module.RDF.nil))
                value = tuple(map(term, graph.items(head)))
            elif operation == 'namespace':
                graph.bind('ex', module.URIRef('https://example.org/'))
                value = graph.qname(module.URIRef('https://example.org/x')), [(p, str(ns)) for p, ns in graph.namespaces()]
            else:
                resource = graph.resource(a)
                value = type(resource).__name__, term(resource.identifier), tuple(term(x.identifier) for x in resource.objects(p))
            results.append(value)
        finally:
            graph.close()
    assert results[0] == results[1]


@pytest.mark.parametrize('selected', [False, True])
@pytest.mark.parametrize('destination', [False, True])
def test_graph_skolemization_contract(selected, destination):
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        blank = module.BNode('node')
        graph.add((blank, module.URIRef('urn:p'), module.Literal('v')))
        target = module.Graph() if destination else None
        converted = graph.skolemize(new_graph=target, bnode=blank if selected else None)
        restored = converted.de_skolemize()
        results.append((sorted(map(term, converted)), sorted(map(term, restored)),
                        converted is target, len(converted.de_skolemize(uriref=blank.skolemize()))))
    assert results[0] == results[1]


def test_uri_de_skolemize_requires_genid_type():
    for module in (rdflib, rdfcore):
        with pytest.raises(Exception):
            module.BNode('node').skolemize().de_skolemize()


@pytest.mark.parametrize('sqlite', [False, True])
def test_genid_identity_and_store_roundtrip(sqlite):
    results = []
    for module in (rdflib, rdfcore):
        import importlib
        terms = importlib.import_module(module.__name__ + '.term')
        graph = module.Graph(**({'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}))
        p, o = module.URIRef('urn:p'), module.Literal('value')
        for cls in (module.URIRef, terms.Genid, terms.RDFLibGenid):
            graph.add((cls('https://e/.well-known/genid/rdflib/node'), p, o))
        results.append((len(graph), sorted(type(s).__name__ for s in graph.subjects())))
        graph.close()
        raw = module.BNode('node').skolemize()
        assert terms.RDFLibGenid(raw).de_skolemize() == module.BNode('node')
        external = terms.Genid('https://e/.well-known/genid/node')
        assert external.de_skolemize() == external.de_skolemize()
    assert results[0] == results[1]


@pytest.mark.parametrize('kind', ['URIRef', 'BNode'])
def test_graph_n3_representation(kind):
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(identifier=getattr(module, kind)('urn:graph'))
        results.append(graph.n3())
    assert results[0] == results[1]


@pytest.mark.parametrize('method', ['subjects', 'predicates', 'objects', 'predicate_objects', 'subject_predicates', 'subject_objects'])
@pytest.mark.parametrize('unique', [False, True])
@pytest.mark.parametrize('sqlite', [False, True])
def test_projection_iterators_keep_types_and_duplicate_contract(method, unique, sqlite):
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(**({'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}))
        s, p, o = [module.URIRef('urn:' + x) for x in 'spo']
        graph.add((s, p, o)).add((o, p, o))
        results.append(sorted(map(term, getattr(graph, method)(unique=unique))))
        graph.close()
    assert results[0] == results[1]


def test_dataset_graph_views_preserve_previous_base_and_identity():
    results = []
    for module in (rdflib, rdfcore):
        dataset = module.Dataset(default_graph_base='urn:default-base')
        first = dataset.graph(module.URIRef('urn:named'), base='urn:first')
        second = dataset.graph(module.URIRef('urn:named'))
        default_view = dataset.graph(dataset.default_graph.identifier, base='urn:view')
        results.append((first is second, first.base, second.base,
                        default_view is dataset.default_graph, default_view.base,
                        dataset.default_graph.base,
                        dataset.namespace_manager is dataset.default_graph.namespace_manager,
                        isinstance(dataset, module.ConjunctiveGraph)))
    assert results[0] == results[1]


def test_generated_dataset_graph_binds_genid_namespace():
    results = []
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        graph = dataset.graph()
        results.append((type(graph.identifier).__name__, [(p, str(ns)) for p, ns in dataset.namespaces() if p == 'genid']))
    assert results[0] == results[1]


def test_dataset_quad_selector_and_query_side_effects():
    results = []
    for module in (rdflib, rdfcore):
        graph = module.Dataset()
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph.add(triple).add((*triple, module.URIRef('urn:named')))
        selected = list(graph.quads((*triple, module.URIRef('urn:named'))))
        before = {str(c.identifier) for c in graph.graphs()}
        assert list(graph.quads((None, None, None, module.URIRef('urn:missing')))) == []
        after = {str(c.identifier) for c in graph.graphs()}
        results.append((sorted(map(term, selected)), before, after, sorted(map(term, graph.triples(None)))))
    assert results[0] == results[1]


def test_choices_respects_native_store_override():
    for module in (rdflib, rdfcore):
        called = []
        class Custom(type(module.Graph().store)):
            def triples_choices(self, triple, context=None):
                called.append('choices')
                yield from super().triples_choices(triple, context)
        for kind in ('Graph', 'Dataset', 'ConjunctiveGraph'):
            graph = getattr(module, kind)(store=Custom())
            triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
            graph.add(triple)
            assert list(graph.triples_choices(([triple[0]], None, None))) == [triple]
        assert called == ['choices'] * 3


def test_inplace_add_delegates_bulk_and_inherited_lifecycle_is_shared():
    for module in (rdflib, rdfcore):
        calls = []
        class Custom(type(module.Graph().store)):
            def addN(self, quads):
                calls.append('bulk')
                return super().addN(quads)
        graph = module.Graph(store=Custom())
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph += [triple]
        assert calls == ['bulk']
        assert triple in graph
        for name in ('open', 'close', 'commit', 'rollback', 'destroy'):
            assert getattr(module.ConjunctiveGraph, name) is getattr(module.Graph, name)


def test_known_context_views_do_not_call_overridden_factory():
    for module in (rdflib, rdfcore):
        class Custom(module.ConjunctiveGraph):
            def get_context(self, *args, **kwargs):
                raise AssertionError('known contexts must not invoke the graph factory')
        graph = Custom(identifier=module.URIRef('urn:known'))
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph.add(triple)
        assert next(graph.contexts()) is graph.default_context
        assert next(graph.quads())[3] is graph.default_context


def test_namespace_initialization_and_iterator_errors_are_lazy():
    results = []
    for module in (rdflib, rdfcore):
        stages = []
        try:
            graph = module.Graph(bind_namespaces='invalid')
            stages.append('constructed')
            iterator = graph.namespaces()
            stages.append('iterator-created')
            next(iterator)
        except Exception as error:
            stages.append(type(error).__name__)
        results.append(stages)
    assert results[0] == results[1]
