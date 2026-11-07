"""Graph lifecycle forwarding against the pinned executable reference."""

import pytest
import rdfcore


def test_sqlite_graph_rollback_is_effective():
    graph = rdfcore.Graph(store=rdfcore.SQLiteStore())
    triple = tuple(rdfcore.URIRef("urn:" + x) for x in "spo")
    try:
        with graph.store.transaction():
            graph.add(triple)
            assert graph.rollback() is graph
            assert len(graph) == 0
            with pytest.raises(RuntimeError, match="transaction"):
                graph.commit()
        graph.add(triple)
        assert graph.commit() is graph
        assert len(graph) == 1
        with pytest.raises(NotImplementedError):
            graph.destroy("unrelated.db")
    finally:
        graph.close()


def test_sqlite_open_reopen_and_configuration(tmp_path):
    path, other = tmp_path / "graph.db", tmp_path / "other.db"
    other.write_bytes(b"untouched")
    store = rdfcore.SQLiteStore(path)
    graph = rdfcore.Graph(store=store, identifier=rdfcore.URIRef("urn:graph"))
    triple = tuple(rdfcore.URIRef("urn:" + x) for x in "spo")
    graph.add(triple)
    assert graph.open(path) == 1
    with pytest.raises(RuntimeError):
        graph.open(other)
    graph.close()
    assert graph.open(path) == 1
    assert triple in graph
    graph.close()
    missing = tmp_path / "missing.db"
    assert graph.open(missing, create=False) == -1
    assert not missing.exists()
    assert graph.open(missing, create=True) == 1
    assert len(graph) == 0
    graph.close()
    assert other.read_bytes() == b"untouched"
