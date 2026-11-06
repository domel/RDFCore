"""Graph lifecycle forwarding against the pinned executable reference."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('kind', ['Graph', 'Dataset'])
def test_store_lifecycle_forwarding(kind):
    for module in (rdflib, rdfcore):
        calls = []
        class Recording(module.store.Store):
            context_aware = graph_aware = True
            def open(self, configuration, create=False):
                calls.append(('open', configuration, create))
                return 19
            def close(self, commit_pending_transaction=False):
                calls.append(('close', commit_pending_transaction))
                return 23
            def commit(self): calls.append(('commit',))
            def rollback(self): calls.append(('rollback',))
            def destroy(self, configuration): calls.append(('destroy', configuration))
        graph = getattr(module, kind)(store=Recording())
        assert graph.open('configuration', True) == 19
        assert graph.commit() is graph
        assert graph.rollback() is graph
        assert graph.destroy('configuration') is graph
        assert graph.close(True) == 23
        assert calls == [('open', 'configuration', True), ('commit',), ('rollback',),
                         ('destroy', 'configuration'), ('close', True)]


def test_sqlite_graph_rollback_is_effective():
    graph = rdfcore.Graph(store=rdfcore.SQLiteStore())
    triple = tuple(rdfcore.URIRef('urn:' + x) for x in 'spo')
    try:
        with graph.store.transaction():
            graph.add(triple)
            assert graph.rollback() is graph
            assert len(graph) == 0
            with pytest.raises(RuntimeError, match='transaction'):
                graph.commit()
        graph.add(triple)
        assert graph.commit() is graph
        assert len(graph) == 1
        with pytest.raises(NotImplementedError):
            graph.destroy('unrelated.db')
    finally:
        graph.close()


def test_sqlite_open_reopen_and_configuration(tmp_path):
    path, other = tmp_path / 'graph.db', tmp_path / 'other.db'
    other.write_bytes(b'untouched')
    store = rdfcore.SQLiteStore(path)
    graph = rdfcore.Graph(store=store, identifier=rdfcore.URIRef('urn:graph'))
    triple = tuple(rdfcore.URIRef('urn:' + x) for x in 'spo')
    graph.add(triple)
    assert graph.open(path) == 1
    with pytest.raises(RuntimeError):
        graph.open(other)
    graph.close()
    assert graph.open(path) == 1
    assert triple in graph
    graph.close()
    missing = tmp_path / 'missing.db'
    assert graph.open(missing, create=False) == -1
    assert not missing.exists()
    assert graph.open(missing, create=True) == 1
    assert len(graph) == 0
    graph.close()
    assert other.read_bytes() == b'untouched'


def test_sqlite_nested_rollback_preserves_outer_writes(tmp_path):
    graph = rdfcore.Graph(store=rdfcore.SQLiteStore(tmp_path / 'nested.db'))
    s, p, o = [rdfcore.URIRef('urn:' + x) for x in 'spo']
    try:
        with graph.store.transaction():
            graph.add((s, p, o))
            with graph.store.transaction():
                graph.add((o, p, s))
                assert graph.rollback() is graph
            assert set(graph) == {(s, p, o)}
        assert set(graph) == {(s, p, o)}
    finally:
        graph.close()


def test_sqlite_failed_reopen_keeps_data_and_other_files(tmp_path):
    import sqlite3
    path, other = tmp_path / 'valid.db', tmp_path / 'unrelated.txt'
    other.write_bytes(b'not a database')
    graph = rdfcore.Graph(store=rdfcore.SQLiteStore(path), identifier=rdfcore.URIRef('urn:g'))
    triple = tuple(rdfcore.URIRef('urn:' + x) for x in 'spo')
    graph.add(triple)
    graph.close()
    with pytest.raises(sqlite3.DatabaseError):
        graph.open(other)
    assert graph.store.path == str(path)
    assert other.read_bytes() == b'not a database'
    assert graph.open(path) == 1
    assert triple in graph
    graph.close()
    graph.close()
