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
