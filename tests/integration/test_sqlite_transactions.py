import pytest

from rdfcore import Literal, SQLiteStore, URIRef


def triple(value):
    return URIRef('urn:s'), URIRef('urn:p'), Literal(value)


def test_transaction_commits_once_and_persists(tmp_path):
    path = tmp_path / 'transactions.sqlite'
    store = SQLiteStore(path)
    statements = []
    store._connection.set_trace_callback(statements.append)
    with store.transaction():
        store.add(triple('a'))
        store.add(triple('b'))
    assert sum(sql.startswith('RELEASE') for sql in statements) == 1
    store.close()
    reopened = SQLiteStore(path)
    assert len(reopened) == 2
    reopened.close()


def test_failed_transaction_restores_removals():
    store = SQLiteStore()
    store.add(triple('original'))
    with pytest.raises(RuntimeError):
        with store.transaction():
            store.remove((None, None, None))
            store.add(triple('new'))
            raise RuntimeError('abort')
    assert next(store.triples((None, None, None)))[0] == triple('original')
    store.close()


def test_nested_transaction_rollback_is_local():
    store = SQLiteStore()
    with store.transaction():
        store.add(triple('outer'))
        with pytest.raises(ValueError):
            with store.transaction():
                store.add(triple('inner'))
                raise ValueError('abort inner')
        assert len(store) == 1
    assert len(store) == 1
    store.close()


def test_bulk_add_is_atomic_on_generator_failure():
    store = SQLiteStore()
    def broken():
        yield triple('a')
        raise ValueError('bad input')
    with pytest.raises(ValueError):
        store.add_many(broken())
    assert len(store) == 0
    assert store.add_many([triple('a'), triple('a')]) == 2
    assert len(store) == 1
    store.close()


@pytest.mark.parametrize('size', [0, 1, 1024, 1025, 2050])
@pytest.mark.parametrize('context', [None, URIRef('urn:g')])
def test_bulk_count_duplicates_and_persistence(tmp_path, size, context):
    path = tmp_path / 'bulk.sqlite'
    store = SQLiteStore(path)
    try:
        assert store.add_many((triple(i // 2) for i in range(size)), context) == size
    finally:
        store.close()
    store = SQLiteStore(path)
    try:
        assert len(store) == (size + 1) // 2
        assert (context in set(store.contexts())) == (size > 0 and context is not None)
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['generator', 'codec', 'arity'])
def test_bulk_failure_restores_contexts_and_outer_transaction(tmp_path, failure):
    store = SQLiteStore(tmp_path / 'rollback.sqlite')
    existing, added = URIRef('urn:existing'), URIRef('urn:added')
    def broken():
        for i in range(1100):
            yield triple(i)
        if failure == 'generator':
            raise RuntimeError('source failed')
        if failure == 'codec':
            yield URIRef('urn:s'), URIRef('urn:p'), object()
        else:
            yield URIRef('urn:s'), URIRef('urn:p')
    import sqlite3
    try:
        with store.transaction():
            store.add(triple('before'), existing)
            with pytest.raises({'generator': RuntimeError, 'codec': TypeError, 'arity': sqlite3.ProgrammingError}[failure]):
                store.add_many(broken(), added)
            assert len(store) == 1
            assert set(store.contexts()) == {existing}
            store.add(triple('after'), existing)
        assert len(store) == 2
        assert store._transaction_depth == 0
    finally:
        store.close()


def test_bulk_generator_observes_previous_writes():
    store = SQLiteStore()
    context = URIRef('urn:g')
    def source():
        yield triple('first')
        assert len(store) == 1
        assert context in set(store.contexts())
        store.remove_context(context)
        yield triple('second')
        assert len(store) == 1
        assert context in set(store.contexts())
    try:
        assert store.add_many(source(), context) == 2
        assert next(store.triples((None, None, None)))[0] == triple('second')
    finally:
        store.close()


def test_bulk_preserves_subclass_add_override():
    class CustomStore(SQLiteStore):
        def add(self, triple, context=None, quoted=False):
            return super().add((*triple[:2], Literal('custom')), context, quoted)
    store = CustomStore()
    try:
        assert store.add_many([triple('original')]) == 1
        assert next(store.triples((None, None, None)))[0] == triple('custom')
    finally:
        store.close()


def test_bulk_uses_lazy_executemany():
    store = SQLiteStore()
    class ConnectionSpy:
        def __init__(self, connection):
            self.connection = connection
            self.bulk_calls = 0

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def executemany(self, sql, rows):
            self.bulk_calls += 1
            assert iter(rows) is rows
            return self.connection.executemany(sql, rows)
    spy = ConnectionSpy(store._connection)
    store._connection = spy
    try:
        assert store.add_many((triple(i) for i in range(5))) == 5
        assert spy.bulk_calls == 1
    finally:
        store.close()
