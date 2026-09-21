"""Store interfaces and the in-memory RDF store."""

from __future__ import annotations

from collections import defaultdict
import pickle
import sqlite3

class Store:
    context_aware = False
    formula_aware = False
    transaction_aware = False
    graph_aware = False

    def open(self, configuration=None, create=False):
        return self

    def close(self, commit_pending_transaction=False):
        return None

    def add(self, triple, context, quoted=False):
        raise NotImplementedError

    def remove(self, triple, context=None):
        raise NotImplementedError

    def triples(self, triple_pattern, context=None):
        raise NotImplementedError

    def __len__(self, context=None):
        raise NotImplementedError


class Memory(Store):
    context_aware = True
    graph_aware = True

    def __init__(self, configuration=None):
        self._triples: set[tuple] = set()
        self._contexts: dict[object, set[tuple]] = defaultdict(set)
        self._sp = defaultdict(set)
        self._po = defaultdict(set)
        self._os = defaultdict(set)

    def add(self, triple, context=None, quoted=False):
        subject, predicate, obj = triple
        if triple in self._triples:
            self._contexts[context].add(triple)
            return triple
        self._triples.add(triple)
        self._contexts[context].add(triple)
        self._sp[(subject, predicate)].add(obj)
        self._po[(predicate, obj)].add(subject)
        self._os[(obj, subject)].add(predicate)
        return triple

    def remove(self, triple, context=None):
        subject, predicate, obj = triple
        if subject is None or predicate is None or obj is None:
            matches = list(self.triples((subject, predicate, obj), context))
            for item in matches:
                self.remove(item[0], context)
            return
        if context is not None:
            self._contexts[context].discard(triple)
            if not self._contexts[context]:
                self._contexts.pop(context, None)
            if any(triple in values for values in self._contexts.values()):
                return
        else:
            for values in self._contexts.values():
                values.discard(triple)
        if triple in self._triples:
            self._triples.remove(triple)
            self._sp[(subject, predicate)].discard(obj)
            self._po[(predicate, obj)].discard(subject)
            self._os[(obj, subject)].discard(predicate)

    def triples(self, triple_pattern, context=None):
        subject, predicate, obj = triple_pattern
        # ``None`` is the store-level union query. Graph instances always pass
        # a concrete context identifier, including their default graph.
        available = set(self._triples if context is None else self._contexts.get(context, ()))
        candidates = available
        if subject is not None and predicate is not None:
            candidates = ((subject, predicate, item) for item in self._sp.get((subject, predicate), ()) if (subject, predicate, item) in available)
        elif predicate is not None and obj is not None:
            candidates = ((item, predicate, obj) for item in self._po.get((predicate, obj), ()) if (item, predicate, obj) in available)
        elif subject is not None and obj is not None:
            candidates = ((subject, item, obj) for item in self._os.get((obj, subject), ()) if (subject, item, obj) in available)
        for triple in candidates:
            if all(value is None or value == actual for value, actual in zip(triple_pattern, triple)):
                yield triple, (context,) if context is not None else ()

    def contexts(self, triple=None):
        for context, triples in self._contexts.items():
            if triples and (triple is None or triple in triples):
                yield context

    def __len__(self, context=None):
        return len(self._triples if context is None else self._contexts.get(context, ()))

    def remove_context(self, context):
        self.remove((None, None, None), context)
        self._contexts.pop(context, None)


class SQLiteStore(Store):
    """Small disk-backed RDF store using SQLite and indexed term blobs.

    The store keeps one row per ``(triple, context)``.  Terms are serialized
    with pickle solely for the private on-disk representation; queries still
    use SQLite's indexed byte columns and do not materialize the dataset.
    """

    context_aware = True
    graph_aware = True

    def __init__(self, path=":memory:"):
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS triples ("
            "s BLOB NOT NULL, p BLOB NOT NULL, o BLOB NOT NULL, "
            "context BLOB NOT NULL, PRIMARY KEY (s, p, o, context))"
        )
        self._connection.execute("CREATE INDEX IF NOT EXISTS triples_spo ON triples (s, p, o)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS triples_pos ON triples (p, o, s)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS triples_osp ON triples (o, s, p)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS triples_context ON triples (context)")
        self._connection.commit()

    @staticmethod
    def _encode(value):
        return sqlite3.Binary(pickle.dumps(value, protocol=4))

    @staticmethod
    def _decode(value):
        return pickle.loads(value)

    def add(self, triple, context=None, quoted=False):
        values = tuple(self._encode(item) for item in (*triple, context))
        self._connection.execute("INSERT OR IGNORE INTO triples VALUES (?, ?, ?, ?)", values)
        self._connection.commit()
        return triple

    def remove(self, triple, context=None):
        pattern = tuple(triple)
        if len(pattern) != 3:
            raise ValueError("triple pattern must contain three elements")
        clauses, values = [], []
        for column, value in zip(("s", "p", "o"), pattern):
            if value is not None:
                clauses.append(f"{column} = ?")
                values.append(self._encode(value))
        if context is not None:
            clauses.append("context = ?")
            values.append(self._encode(context))
        where = " AND ".join(clauses) or "1"
        self._connection.execute(f"DELETE FROM triples WHERE {where}", values)
        self._connection.commit()

    def triples(self, triple_pattern, context=None):
        if len(triple_pattern) != 3:
            raise ValueError("triple pattern must contain three elements")
        clauses, values = [], []
        for column, value in zip(("s", "p", "o"), triple_pattern):
            if value is not None:
                clauses.append(f"{column} = ?")
                values.append(self._encode(value))
        if context is not None:
            clauses.append("context = ?")
            values.append(self._encode(context))
        where = " AND ".join(clauses) or "1"
        columns = "s, p, o, context" if context is not None else "DISTINCT s, p, o"
        cursor = self._connection.execute(f"SELECT {columns} FROM triples WHERE {where}", values)
        for row in cursor:
            subject, predicate, obj = row[:3]
            decoded = tuple(self._decode(value) for value in (subject, predicate, obj))
            yield decoded, (self._decode(row[3]),) if context is not None else ()

    def contexts(self, triple=None):
        if triple is None:
            cursor = self._connection.execute("SELECT DISTINCT context FROM triples")
        else:
            encoded = [self._encode(value) for value in triple]
            cursor = self._connection.execute(
                "SELECT DISTINCT context FROM triples WHERE s = ? AND p = ? AND o = ?", encoded
            )
        for (context,) in cursor:
            yield self._decode(context)

    def __len__(self, context=None):
        if context is None:
            return self._connection.execute(
                "SELECT COUNT(*) FROM (SELECT 1 FROM triples GROUP BY s, p, o)"
            ).fetchone()[0]
        encoded = self._encode(context)
        return self._connection.execute("SELECT COUNT(*) FROM triples WHERE context = ?", (encoded,)).fetchone()[0]

    def remove_context(self, context):
        self._connection.execute("DELETE FROM triples WHERE context = ?", (self._encode(context),))
        self._connection.commit()

    def close(self, commit_pending_transaction=False):
        self._connection.commit()
        self._connection.close()
