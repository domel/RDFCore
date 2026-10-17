import pickle
import sqlite3

import pytest

from rdfcore import BNode, Literal, SQLiteStore, TripleTerm, URIRef


def test_equal_language_literals_have_same_storage_key():
    store = SQLiteStore()
    triple = (URIRef('urn:s'), URIRef('urn:p'), Literal('text', lang='EN'))
    store.add(triple)
    store.add((*triple[:2], Literal('text', lang='en')))
    assert len(store) == 1
    store.close()


def test_codec_roundtrip():
    values = [None, URIRef('urn:x'), BNode('x'), Literal('01', datatype='urn:t', normalize=False),
              Literal('text', lang='en', direction='rtl'),
              TripleTerm(BNode('s'), URIRef('urn:p'), Literal('x'))]
    for value in values:
        assert SQLiteStore._decode(SQLiteStore._encode(value)) == value


def test_legacy_database_migrates(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE triples (s BLOB, p BLOB, o BLOB, context BLOB, PRIMARY KEY(s,p,o,context))')
    triple = (URIRef('urn:s'), URIRef('urn:p'), Literal('x'))
    connection.execute('INSERT INTO triples VALUES (?,?,?,?)',
                       [pickle.dumps(term, protocol=4) for term in (*triple, None)])
    connection.commit()
    connection.close()
    store = SQLiteStore(path)
    assert next(store.triples((None, None, None)))[0] == triple
    assert store._connection.execute('PRAGMA user_version').fetchone()[0] == 1
    store.close()


def test_unknown_database_version_is_rejected(tmp_path):
    path = tmp_path / 'future.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('PRAGMA user_version=999')
    with pytest.raises(ValueError, match='version'):
        SQLiteStore(path)


@pytest.mark.parametrize('bad', [b'cbuiltins\neval\n.', b'not a pickle'])
def test_failed_legacy_migration_preserves_rows_and_version(tmp_path, bad):
    path = tmp_path / 'invalid.sqlite'
    good = [pickle.dumps(term, protocol=4) for term in
            (URIRef('urn:s'), URIRef('urn:p'), Literal('x'), None)]
    rows = [tuple(good), (bad, *good[1:])]
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE triples (s BLOB, p BLOB, o BLOB, context BLOB, PRIMARY KEY(s,p,o,context))')
        connection.executemany('INSERT INTO triples VALUES (?,?,?,?)', rows)
    with pytest.raises((ValueError, pickle.UnpicklingError)):
        SQLiteStore(path)
    with sqlite3.connect(path) as connection:
        assert set(connection.execute('SELECT * FROM triples')) == set(rows)
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 0


def test_legacy_nested_terms_and_datatypes(tmp_path):
    from datetime import datetime
    from decimal import Decimal
    path = tmp_path / 'typed.sqlite'
    values = [Literal(Decimal('1.25')), Literal(datetime(2026, 1, 1)),
              Literal('text', lang='EN', direction='rtl'),
              TripleTerm(BNode('s'), URIRef('urn:p'), Literal('x'))]
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE triples (s BLOB, p BLOB, o BLOB, context BLOB, PRIMARY KEY(s,p,o,context))')
        for i, value in enumerate(values):
            connection.execute('INSERT INTO triples VALUES (?,?,?,?)',
                [pickle.dumps(term, protocol=4) for term in
                 (URIRef(f'urn:s{i}'), URIRef('urn:p'), value, URIRef('urn:g'))])
    store = SQLiteStore(path)
    for i, value in enumerate(values):
        restored = next(store.triples((URIRef(f'urn:s{i}'), None, None)))[0][2]
        assert restored == value
        assert hash(restored) == hash(value)
        if isinstance(value, Literal) and value.language:
            assert restored.language == value.language
    store.close()


def test_language_forms_are_context_local_and_union_retains_first_spelling(tmp_path):
    import rdfcore
    import rdflib
    def observe(module, store=None):
        dataset = module.Dataset(**({'store': store} if store is not None else {}))
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        g, h = (dataset.graph(module.URIRef(name)) for name in ('urn:g', 'urn:h'))
        g.add((s, p, module.Literal('v', lang='EN')))
        h.add((s, p, module.Literal('v', lang='en')))
        union = lambda: next(dataset.store.triples((None, None, None), None))[0][2].language
        initial = next(g.objects()).language, next(h.objects()).language, union()
        dataset.remove_graph(g)
        surviving = union()
        dataset.remove_graph(h)
        h.add((s, p, module.Literal('v', lang='eN')))
        return initial, surviving, union()
    store = SQLiteStore(tmp_path/'contexts.sqlite')
    try:
        assert observe(rdfcore, store) == observe(rdflib)
    finally:
        store.close()


def test_nested_language_forms_bulk_rollback_and_reopen(tmp_path):
    path = tmp_path/'nested.sqlite'
    store = SQLiteStore(path)
    s, p, g = map(URIRef, ('urn:s', 'urn:p', 'urn:g'))
    term = TripleTerm(s, p, Literal('v', lang='EN', direction='rtl'))
    with pytest.raises(RuntimeError):
        with store.transaction():
            store.add_many([(s, p, term)], g)
            raise RuntimeError('rollback')
    assert len(store) == 0
    assert store._connection.execute('SELECT COUNT(*) FROM lexical_forms').fetchone()[0] == 0
    store.add_many([(s, p, term)], g)
    store.close()
    store = SQLiteStore(path)
    try:
        restored = next(store.triples((None, None, None), g))[0][2]
        assert restored.object.language == 'EN'
        assert restored == term
        store.remove((None, None, None), g)
        assert store._connection.execute('SELECT COUNT(*) FROM lexical_forms').fetchone()[0] == 0
    finally:
        store.close()


def test_canonical_version_one_database_stays_readable(tmp_path):
    from rdfcore.codec import encode
    path = tmp_path/'v1.sqlite'
    terms = URIRef('urn:s'), URIRef('urn:p'), Literal('v', lang='en'), URIRef('urn:g')
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE triples (s BLOB,p BLOB,o BLOB,context BLOB,PRIMARY KEY(s,p,o,context))')
        connection.execute('INSERT INTO triples VALUES (?,?,?,?)', tuple(encode(term) for term in terms))
        connection.execute('PRAGMA user_version=1')
    store = SQLiteStore(path)
    try:
        store.add((terms[0], terms[1], Literal('v', lang='EN')), terms[3])
        assert len(store) == 1
        assert next(store.triples((None, None, None), terms[3]))[0][2].language == 'en'
    finally:
        store.close()


def test_language_forms_written_by_another_open_store_are_visible(tmp_path):
    path = tmp_path/'shared.sqlite'
    reader, writer = SQLiteStore(path), SQLiteStore(path)
    s, p, g = map(URIRef, ('urn:s', 'urn:p', 'urn:g'))
    try:
        writer.add((s, p, Literal('v', lang='EN')), g)
        assert next(reader.triples((None, None, None), g))[0][2].language == 'EN'
        reader.remove((None, None, None), g)
        reader.add((s, p, Literal('v', lang='eN')), g)
        assert next(writer.triples((None, None, None), g))[0][2].language == 'eN'
    finally:
        reader.close()
        writer.close()


def test_union_deduplicates_identity_before_joining_spellings():
    store = SQLiteStore()
    calls = []
    try:
        triple = URIRef('urn:s'), URIRef('urn:p'), Literal('v', lang='EN')
        for graph in ('urn:g', 'urn:h'):
            store.add(triple, URIRef(graph))
        store._connection.set_trace_callback(calls.append)
        assert len(list(store.triples((None, None, None)))) == 1
        query = next(call for call in calls if call.startswith('SELECT'))
        assert 'FROM (SELECT DISTINCT' in query
    finally:
        store.close()
