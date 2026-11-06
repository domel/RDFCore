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
