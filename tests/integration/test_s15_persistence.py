"""Persistence and corruption regressions for S15 (internal contracts)."""

import pickle
import sqlite3
import subprocess
import sys

import pytest
from rdfcore import Literal, SQLiteStore, URIRef
from rdfcore.codec import decode


@pytest.mark.parametrize(
    "payload",
    [
        b'[["x"],"y"]',
        b'[{},"x"]',
        b'["uri",1]',
        b'["literal","v",null,null,"ltr"]',
        b'["uri","x"]trailing',
        b'["uri",',
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_codec_rejects_corruption(payload):
    with pytest.raises(ValueError):
        decode(payload)


def test_failed_migration_preserves_entire_schema(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE triples (s BLOB,p BLOB,o BLOB,context BLOB,PRIMARY KEY(s,p,o,context))"
        )
        db.execute("INSERT INTO triples VALUES (?,?,?,?)", (b"forbidden",) * 4)
    original = path.read_bytes()
    with pytest.raises((ValueError, pickle.UnpicklingError)):
        SQLiteStore(path)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "phase", ["before_commit", "after_commit", "after_metadata", "after_triple"]
)
def test_process_exit_preserves_only_committed_batch(tmp_path, phase):
    path = tmp_path / "crash.db"
    SQLiteStore(path).close()
    code = """
import os,sys
from rdfcore import SQLiteStore,URIRef,Literal
class Store(SQLiteStore):
 def _remember_lexical_forms(self,*args,**kwargs):
  super()._remember_lexical_forms(*args,**kwargs)
  if sys.argv[2]=='after_metadata':os._exit(0)
 def _register_context(self,*args,**kwargs):
  if sys.argv[2]=='after_triple':os._exit(0)
  return super()._register_context(*args,**kwargs)
s=Store(sys.argv[1])
with s.transaction():
 s.add((URIRef('urn:s'),URIRef('urn:p'),Literal('v',lang='EN')),URIRef('urn:g'))
 if sys.argv[2]=='before_commit':os._exit(0)
os._exit(0)
"""
    subprocess.run([sys.executable, "-c", code, str(path), phase], check=True)
    store = SQLiteStore(path)
    try:
        assert len(store) == int(phase == "after_commit")
        assert len(list(store.contexts())) == int(phase == "after_commit")
        assert store._connection.execute(
            "SELECT COUNT(*) FROM lexical_forms"
        ).fetchone()[0] == 2 * int(phase == "after_commit")
    finally:
        store.close()


def test_concurrent_reader_writer_and_lock_recovery(tmp_path):
    path = tmp_path / "shared.db"
    reader, writer = SQLiteStore(path), SQLiteStore(path)
    row = URIRef("urn:s"), URIRef("urn:p"), Literal("v", lang="EN")
    reader._connection.execute("PRAGMA busy_timeout=0")
    try:
        with writer.transaction():
            writer.add(row, URIRef("urn:g"))
            assert len(reader) == 0
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                reader.add_many([row])
            assert reader._transaction_depth == 0
        assert next(reader.triples((None, None, None)))[0][2].language == "EN"
        assert reader.add_many([row]) == 1
        assert len(reader) == 1
    finally:
        reader.close()
        writer.close()


def test_release_failure_rolls_back_data_and_views():
    from rdfcore import Dataset

    store = SQLiteStore()
    ds = Dataset(store=store)

    class FailingRelease:
        failed = False

        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def execute(self, sql, *args):
            if sql.startswith("RELEASE") and not self.failed:
                self.failed = True
                raise sqlite3.OperationalError("disk I/O error")
            return self.connection.execute(sql, *args)

    store._connection = FailingRelease(store._connection)
    try:
        with pytest.raises(sqlite3.OperationalError, match="I/O"):
            with store.transaction():
                ds.graph(URIRef("urn:g"), base="urn:aborted").add(
                    (URIRef("urn:s"), URIRef("urn:p"), Literal("v", lang="EN"))
                )
        assert len(ds) == 0
        assert not store._connection.in_transaction
        assert store._transaction_depth == 0
        assert not store._has_lexical_forms
        graph = ds.graph(URIRef("urn:g"), base="urn:current")
        assert next(g for g in ds.graphs() if g.identifier == graph.identifier) is graph
    finally:
        store.close()


def test_hostile_legacy_pickle_does_not_execute(tmp_path):
    from rdfcore.codec import decode_legacy

    marker = tmp_path / "executed"

    class Hostile:
        def __reduce__(self):
            return eval, (
                f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')",
            )

    with pytest.raises(ValueError, match="forbidden"):
        decode_legacy(pickle.dumps(Hostile()))
    assert not marker.exists()


def test_codec_depth_limit_and_trailing_legacy_data():
    from rdfcore import TripleTerm
    from rdfcore.codec import MAX_DEPTH, encode, decode_legacy

    s, p = URIRef("urn:s"), URIRef("urn:p")
    value = Literal("v")
    for _ in range(MAX_DEPTH):
        value = TripleTerm(s, p, value)
    assert decode(encode(value)) == value
    with pytest.raises(ValueError, match="nesting"):
        encode(TripleTerm(s, p, value))
    with pytest.raises(ValueError, match="trailing"):
        decode_legacy(pickle.dumps(s) + b"foreign")


def test_constructor_rejects_foreign_schema_without_writes(tmp_path):
    path = tmp_path / "foreign.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    original = path.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        SQLiteStore(path)
    assert path.read_bytes() == original


def test_automatic_rollback_blocks_remaining_outer_writes():
    store = SQLiteStore()
    key = bytes(store._encode(Literal("inner"))).hex()
    store._connection.execute(
        f"CREATE TRIGGER abort_write BEFORE INSERT ON triples WHEN NEW.o=X'{key}' BEGIN SELECT RAISE(ROLLBACK,'aborted'); END"
    )

    def row(value):
        return URIRef("urn:s"), URIRef("urn:p"), Literal(value)

    try:
        with pytest.raises(RuntimeError, match="rolled back"):
            with store.transaction():
                store.add(row("outer"))
                with pytest.raises(sqlite3.IntegrityError):
                    with store.transaction():
                        store.add(row("inner"))
                store.add(row("after"))
        assert len(store) == 0 and not store._connection.in_transaction
        assert store._transaction_depth == 0
        store.add(row("recovered"))
        assert len(store) == 1
    finally:
        store.close()


def test_rejected_single_add_does_not_leave_spelling_metadata():
    store = SQLiteStore()
    s, p, g = map(URIRef, ("urn:s", "urn:p", "urn:g"))
    try:
        store._connection.execute(
            "CREATE TRIGGER deny BEFORE INSERT ON triples BEGIN SELECT RAISE(ABORT,'denied'); END"
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.add((s, p, Literal("v", lang="EN")), g)
        assert (
            store._connection.execute("SELECT COUNT(*) FROM lexical_forms").fetchone()[
                0
            ]
            == 0
        )
        store._connection.execute("DROP TRIGGER deny")
        store.add((s, p, Literal("v", lang="en")), g)
        assert next(store.triples((None, None, None), g))[0][2].language == "en"
    finally:
        store.close()
