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
