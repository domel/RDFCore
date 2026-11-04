"""Regressions for the six S14 review findings."""
import io
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('sqlite', [False, True])
def test_deleted_context_does_not_keep_foreign_view(sqlite, tmp_path):
    for module in (rdflib, rdfcore):
        options = {'store': rdfcore.SQLiteStore(tmp_path / 'cache.db')} if sqlite and module is rdfcore else {}
        graph = module.ConjunctiveGraph(**options)
        foreign = module.ConjunctiveGraph(identifier=module.URIRef('urn:g'))
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        graph.add((*triple, foreign))
        if module is rdflib:
            graph.store.remove_graph(foreign)
        else:
            graph.remove_graph(foreign)
        graph.get_context(foreign.identifier).add(triple)
        context = next(graph.contexts())
        assert type(context) is module.Graph
        assert context.store is graph.store
        assert len(context) == 1
        graph.close()


def test_bulk_override():
    for module in (rdflib, rdfcore):
        calls = []
        class Custom(type(module.Graph().store)):
            def addN(self, quads):
                calls.append('bulk')
                return super().addN(quads)
        graph = module.ConjunctiveGraph(store=Custom())
        triple = tuple(module.URIRef('urn:' + x) for x in 'spo')
        assert graph.addN([(*triple, module.URIRef('urn:g'))]) is graph
        assert calls == ['bulk']
        assert len(graph) == 1


@pytest.mark.parametrize('argument', ['source', 'location'])
def test_file_uri(argument, tmp_path):
    path = tmp_path / 'input with space.ttl'
    path.write_text('<s> <p> <o> .')
    results = []
    for module in (rdflib, rdfcore):
        graph = module.ConjunctiveGraph().parse(format='turtle', **{argument: path.as_uri()})
        results.append({tuple(map(str, row)) for row in graph})
    assert results[0] == results[1]


def test_context_parser_override():
    for module in (rdflib, rdfcore):
        calls = []
        class Custom(module.Graph):
            def parse(self, source=None, **options):
                calls.append(source)
                return super().parse(source=source, **options)
        graph = module.ConjunctiveGraph()
        context = Custom(store=graph.store)
        graph.default_context = context
        assert graph.parse(data='<urn:s> <urn:p> <urn:o> .', format='turtle') is graph
        assert len(calls) == 1
        assert hasattr(calls[0], 'getByteStream')
        assert len(context) == 1


def test_stream_without_name():
    results = []
    for module in (rdflib, rdfcore):
        stream = io.BytesIO(b'<s> <p> <o> .')
        stream.name = None
        graph = module.ConjunctiveGraph().parse(source=stream, format='turtle')
        results.append(({tuple(map(str, row)) for row in graph}, stream.closed))
    assert results[0] == results[1]


@pytest.mark.parametrize('name', ['default', 'Memory'])
def test_store_registry_override(name, monkeypatch):
    for module in (rdflib, rdfcore):
        class Custom(type(module.Graph().store)):
            pass
        class Entry:
            def getClass(self):
                return Custom
        registry = module.plugin._plugins if module is rdflib else module.plugin._registry
        monkeypatch.setitem(registry, (name, module.store.Store), Entry())
        assert type(module.ConjunctiveGraph(store=name).store) is Custom


def test_sqlite_rollback_restores_removed_context_view():
    graph = rdfcore.ConjunctiveGraph(store=rdfcore.SQLiteStore())
    foreign = rdfcore.ConjunctiveGraph(identifier=rdfcore.URIRef('urn:g'))
    triple = tuple(rdfcore.URIRef('urn:' + x) for x in 'spo')
    graph.add((*triple, foreign))
    try:
        with pytest.raises(RuntimeError), graph.store.transaction():
            graph.remove_graph(foreign)
            raise RuntimeError('abort')
        assert next(graph.contexts()) is foreign
        assert next(graph.quads())[3] is foreign
    finally:
        graph.close()
