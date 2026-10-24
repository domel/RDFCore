import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('error', [NotImplementedError, RuntimeError])
@pytest.mark.parametrize('provided_context', [False, True])
def test_value_diagnostics_do_not_enumerate_custom_store_contexts(error, provided_context):
    for module in (rdflib, rdfcore):
        if module is rdflib:
            from rdflib.plugins.stores.memory import Memory
        else:
            Memory = module.Memory

        class CustomStore(Memory):
            calls = 0

            def contexts(self, *args, **kwargs):
                self.calls += 1
                raise error('context enumeration unavailable')

            def triples(self, pattern, context=None):
                for triple, contexts in super().triples(pattern, context):
                    if context is None:
                        contexts = iter(('provided-context',)) if provided_context else iter(())
                    yield triple, contexts

        store = CustomStore()
        graph = module.Graph(store=store, identifier=module.URIRef('urn:g'))
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        for text in ('first', 'second'):
            graph.add((s, p, module.Literal(text)))
        with pytest.raises(module.exceptions.UniquenessError) as raised:
            graph.value(s, p, any=False)
        assert store.calls == 0
        if provided_context:
            assert 'provided-context' in str(raised.value)
        else:
            assert '(contexts: [])' in str(raised.value)


@pytest.mark.parametrize('stage', ['query', 'contexts'])
@pytest.mark.parametrize('error', [StopIteration, RuntimeError])
@pytest.mark.parametrize('any_value', [True, False])
def test_value_diagnostic_iteration_errors_match_reference(stage, error, any_value):
    for module in (rdflib, rdfcore):
        if module is rdflib:
            from rdflib.plugins.stores.memory import Memory
        else:
            Memory = module.Memory

        class Contexts:
            def __iter__(self):
                raise error('diagnostic failed')

        class CustomStore(Memory):
            def triples(self, pattern, context=None):
                if context is None:
                    if stage == 'query':
                        raise error('diagnostic failed')
                    return ((triple, Contexts()) for triple, _ in super().triples(pattern, context))
                return super().triples(pattern, context)

        graph = module.Graph(store=CustomStore(), identifier=module.URIRef('urn:g'))
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        values = {module.Literal('first'), module.Literal('second')}
        for value in values:
            graph.add((s, p, value))
        if any_value is False and error is RuntimeError:
            with pytest.raises(RuntimeError, match='diagnostic failed'):
                graph.value(s, p, any=any_value)
        else:
            # RDFLib catches StopIteration from the complete diagnostic block
            # and returns the first match, even after detecting ambiguity.
            assert graph.value(s, p, any=any_value) in values


@pytest.mark.parametrize('missing', ['subject', 'predicate', 'object', 'two', 'none'])
@pytest.mark.parametrize('size', [0, 1, 2])
@pytest.mark.parametrize('unique', [False, True])
def test_value_matches_reference(missing, size, unique):
    def observe(module):
        graph = module.Graph()
        s, p, o = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')
        for index in range(size):
            graph.add((s, p, o if index == 0 else module.Literal('y')))
        kwargs = dict(subject=s, predicate=p, object=o, default='fallback', any=not unique)
        for key in ({'two': ['subject', 'object'], 'none': []}.get(missing, [missing])):
            kwargs[key] = None
        try:
            result = graph.value(**kwargs)
            if missing == 'object' and size == 2 and not unique:
                assert result in {module.Literal('x'), module.Literal('y')}
                return 'one of the matching objects'
            return type(result).__name__, str(result)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


def test_value_uses_default_predicate():
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        graph.add((module.URIRef('urn:s'), module.RDF.value, module.Literal('x')))
        assert graph.value(module.URIRef('urn:s')) == module.Literal('x')


@pytest.mark.parametrize('unique', [False, True])
def test_value_consumes_only_required_matches(unique):
    for module in (rdflib, rdfcore):
        class ControlledGraph(module.Graph):
            def objects(self, subject=None, predicate=None, unique=False):
                yield module.Literal('first')
                if not unique_check:
                    raise AssertionError('read beyond first match')
                yield module.Literal('second')
                raise AssertionError('read beyond second match')
        unique_check = unique
        graph = ControlledGraph()
        if unique:
            with pytest.raises(module.exceptions.UniquenessError):
                graph.value(module.URIRef('urn:s'), module.URIRef('urn:p'), any=False)
        else:
            assert graph.value(module.URIRef('urn:s'), module.URIRef('urn:p')) == module.Literal('first')


@pytest.mark.parametrize('accessor,missing', [
    ('objects', 'object'), ('subjects', 'subject'), ('predicates', 'predicate'),
])
@pytest.mark.parametrize('second', [None, False, 0, ''])
def test_value_uniqueness_counts_falsey_iterator_values(accessor, missing, second):
    # Overridden accessors must retain next()/StopIteration semantics, even
    # when their result is not a regular stored RDF term.
    for module in (rdflib, rdfcore):
        def values(self, *args):
            yield module.URIRef('urn:first')
            yield second
            raise AssertionError('read beyond second match')
        controlled = type('ControlledGraph', (module.Graph,), {accessor: values})
        kwargs = dict(subject=module.URIRef('urn:s'), predicate=module.URIRef('urn:p'),
                      object=module.URIRef('urn:o'), any=False)
        kwargs[missing] = None
        with pytest.raises(module.exceptions.UniquenessError):
            controlled().value(**kwargs)


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('view', ['graph', 'default', 'named', 'union'])
@pytest.mark.parametrize('missing', ['subject', 'predicate', 'object'])
@pytest.mark.parametrize('size', [0, 1, 2])
def test_value_context_store_and_default_identity(backend, view, missing, size):
    def observe(module):
        store = module.SQLiteStore(':memory:') if module is rdfcore and backend == 'sqlite' else 'default'
        dataset = module.Dataset(store=store, default_union=view == 'union')
        named = dataset.graph(module.URIRef('urn:named'))
        graph = (module.Graph(store=dataset.store, identifier=module.URIRef('urn:graph'))
                 if view == 'graph' else named if view == 'named' else dataset)
        target = (graph if view in ('graph', 'named') else dataset.default_graph)
        s, p, o = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('')
        base = [s, p, o]
        position = {'subject': 0, 'predicate': 1, 'object': 2}[missing]
        triples = []
        for index in range(size):
            triple = list(base)
            if index:
                triple[position] = module.Literal('other') if missing == 'object' else module.URIRef('urn:other')
            triples.append(tuple(triple))
            target.add(tuple(triple))
            target.add(tuple(triple))  # Duplicates must not create ambiguity.
        # The other context must not affect a selected graph. In the union,
        # it repeats a logical triple instead of adding a new candidate.
        if view in ('default', 'union'):
            named.add(triples[0] if triples else (s, p, module.Literal('unrelated')))
        kwargs = dict(subject=s, predicate=p, object=o)
        kwargs[missing] = None
        results = []
        try:
            for fallback in (None, False, 0, '', object()):
                for flag in (True, False, 0, None, ''):
                    for _ in range(2):
                        try:
                            result = graph.value(**kwargs, default=fallback, any=flag)
                        except module.exceptions.UniquenessError as error:
                            assert flag is False
                            message = str(error)
                            assert 'Uniqueness assumption is not fulfilled.' in message
                            assert 'While trying to find a value for' in message
                            assert 'urn:s' in message and 'urn:p' in message
                            results.append('nonunique')
                        else:
                            pattern = [None if i == position else term for i, term in enumerate(base)]
                            candidates = {t[position] for t in graph.triples(tuple(pattern))}
                            if not candidates:
                                assert result is fallback
                                results.append('default')
                            else:
                                assert result in candidates
                                assert type(result) in (module.URIRef, module.Literal)
                                results.append(('term', type(result).__name__) if len(candidates) > 1 else
                                               ('term', type(result).__name__, result.n3()))
            assert len(target) == size
            return results
        finally:
            dataset.close()
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('value', [None, '', 0, False, ('a', 'b')])
def test_uniqueness_error_constructor_matches_reference(value):
    # RDFLib's percent-formatting itself rejects a multi-item tuple.
    if isinstance(value, tuple):
        for module in (rdflib, rdfcore):
            with pytest.raises(TypeError):
                module.exceptions.UniquenessError(value)
        return
    actual = rdfcore.exceptions.UniquenessError(value)
    expected = rdflib.exceptions.UniquenessError(value)
    assert actual.args == expected.args
    assert str(actual) == str(expected)


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_value_uniqueness_diagnostics_include_union_matches_and_contexts(backend):
    for module in (rdflib, rdfcore):
        store = module.SQLiteStore(':memory:') if module is rdfcore and backend == 'sqlite' else 'default'
        dataset = module.Dataset(store=store)
        selected = dataset.graph(module.URIRef('urn:selected'))
        other = dataset.graph(module.URIRef('urn:other-context'))
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        selected.add((s, p, module.Literal('first')))
        selected.add((s, p, module.Literal('second')))
        other.add((s, p, module.Literal('third')))
        try:
            with pytest.raises(module.exceptions.UniquenessError) as error:
                selected.value(s, p, any=False)
            for value in ('first', 'second', 'third'):
                assert '(urn:s, urn:p, ' + value + ')' in str(error.value)
            for context in ('urn:selected', 'urn:other-context'):
                assert context in str(error.value)
            assert len(selected) == 2 and len(other) == 1
        finally:
            dataset.close()


@pytest.mark.parametrize('accessor,missing', [
    ('objects', 'object'), ('subjects', 'subject'), ('predicates', 'predicate'),
])
def test_value_propagates_iterator_error_without_substituting_default(accessor, missing):
    for module in (rdflib, rdfcore):
        def values(self, *args):
            yield module.URIRef('urn:first')
            raise RuntimeError('iterator failed')
        controlled = type('ControlledGraph', (module.Graph,), {accessor: values})
        kwargs = dict(subject=module.URIRef('urn:s'), predicate=module.URIRef('urn:p'),
                      object=module.URIRef('urn:o'), default='fallback')
        kwargs[missing] = None
        graph = controlled()
        assert graph.value(**kwargs) == module.URIRef('urn:first')
        with pytest.raises(RuntimeError, match='iterator failed'):
            graph.value(**kwargs, any=False)
