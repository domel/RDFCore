"""Regressions from the S13 compatibility review."""
import sqlite3
import pytest
import rdflib
import rdfcore
from benchmarks.audit_api import inventory


def test_bulk_override():
    for module in (rdflib, rdfcore):
        class Recording(type(module.Graph().store)):
            calls = 0
            def addN(self, quads):
                self.calls += 1
                return super().addN(quads)
        store = Recording()
        dataset = module.Dataset(store=store)
        dataset.addN([(module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'), dataset.default_graph)])
        assert store.calls == 1
        assert len(dataset) == 1


@pytest.mark.parametrize('lexical', ['P1MT1H', 'P1Y1DT1H'])
def test_calendar_subtraction(lexical):
    outcomes = []
    for module in (rdflib, rdfcore):
        result = module.Literal('2024-03-31', datatype=module.XSD.date) - module.Literal(lexical, datatype=module.XSD.duration)
        outcomes.append(str(result))
    assert outcomes[0] == outcomes[1]


def test_duration_subtraction_native_result():
    outcomes = []
    for module in (rdflib, rdfcore):
        result = module.Literal('P1D', datatype=module.XSD.duration) - module.Literal('P1M', datatype=module.XSD.duration)
        outcomes.append((str(result), str(getattr(result.value, 'tdelta', None))))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('datatype', ['duration', 'dayTimeDuration', 'yearMonthDuration'])
@pytest.mark.parametrize('lexical', [
    'P0001-01-01T01:02:03', 'P00010101T010203', 'P0001-001T01:02:03',
    'P0001001T010203', 'P0001-99-01T01:02:03', '-P0001-01-01T01:02:03',
])
def test_alternative_duration(datatype, lexical):
    outcomes = []
    for module in (rdflib, rdfcore):
        result = module.Literal(lexical, datatype=module.URIRef(str(module.XSD) + datatype))
        outcomes.append((str(result), result.ill_typed, str(getattr(result.value, 'tdelta', None))))
    assert outcomes[0] == outcomes[1]


def test_inventory_conjunctive_fields():
    rows = {(r['class'], r['method']): r for r in inventory()['members']}
    for name in ('store', 'identifier'):
        assert rows['ConjunctiveGraph', name]['status'] != 'missing'


def test_foreign_database_untouched(tmp_path):
    path = tmp_path / 'foreign.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE unrelated (id INTEGER)')
    original = path.read_bytes()
    store = rdfcore.SQLiteStore()
    store.close()
    with pytest.raises(ValueError, match='schema'):
        store.open(path, create=False)
    assert path.read_bytes() == original


@pytest.mark.parametrize('explicit', [False, True])
def test_rollback_context_views(explicit):
    store = rdfcore.SQLiteStore()
    dataset = rdfcore.Dataset(store=store)
    identifier = rdfcore.URIRef('urn:g')
    try:
        try:
            with store.transaction():
                dataset.graph(identifier, base='urn:aborted')
                if explicit:
                    store.rollback()
                else:
                    raise RuntimeError('abort')
        except RuntimeError:
            pass
        graph = dataset.graph(identifier, base='urn:current')
        visible = next(g for g in dataset.graphs() if g.identifier == identifier)
        assert visible is graph
        assert visible.base == 'urn:current'
    finally:
        store.close()


def test_graph_node_sqlite_roundtrip(tmp_path):
    path = tmp_path / 'graph.db'
    for module in (rdflib, rdfcore):
        store = rdfcore.SQLiteStore(path) if module is rdfcore else type(module.Graph().store)()
        graph = module.Graph(store=store, identifier=module.URIRef('urn:outer'))
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Graph(identifier=module.URIRef('urn:inner')))
        graph.add(triple)
        assert triple in graph
        assert isinstance(next(graph.objects()), module.Graph)
        if module is rdfcore:
            graph.close()
            graph.open(path)
            assert triple in graph
            assert isinstance(next(graph.objects()), module.Graph)
        graph.close()


def test_nested_rollback_restores_first_and_latest_views():
    store = rdfcore.SQLiteStore()
    ds = rdfcore.Dataset(store=store)
    key = rdfcore.URIRef('urn:g')
    original = ds.graph(key, base='urn:original')
    try:
        with pytest.raises(RuntimeError):
            with store.transaction():
                with store.transaction():
                    ds.remove_graph(key)
                    ds.graph(key, base='urn:inner')
                raise RuntimeError('abort outer')
        assert next(g for g in ds.graphs() if g.identifier == key) is original
    finally:
        store.close()


def test_create_initializes_existing_empty_file(tmp_path):
    path = tmp_path / 'empty.db'
    path.touch()
    store = rdfcore.SQLiteStore()
    store.close()
    assert store.open(path, create=True) == 1
    store.close()
