"""Predicate indexes retain the first equal object's representation."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('language', [False, True])
@pytest.mark.parametrize('persistent', [False, True])
def test_predicate_object_representation(tmp_path, language, persistent):
    def exercise(lib, store=None):
        graph = lib.Graph(store=store) if store is not None else lib.Graph()
        s1, s2, p = map(lib.URIRef, ('urn:s1', 'urn:s2', 'urn:p'))
        a, b = ((lib.Literal('x', lang='EN'), lib.Literal('x', lang='en'))
                if language else (lib.Literal(1), lib.Literal('1', datatype=lib.XSD.integer)))
        graph.add((s1, p, a))
        graph.add((s2, p, b))
        def snapshot():
            return sorted((str(s), o.language, o.ill_typed)
                          for s, _, o in graph.triples((None, p, None)))
        results = [snapshot()]
        graph.remove((s1, p, None))
        results.append(snapshot())
        if store is not None:
            identifier = graph.identifier
            store.close()
            store = rdfcore.SQLiteStore(tmp_path / 'terms.db')
            graph = lib.Graph(store=store, identifier=identifier)
        results.append(snapshot())
        graph.remove((None, p, None))
        graph.add((s2, p, b))
        results.append(snapshot())
        if store is not None:
            store.close()
        return results
    expected = exercise(rdflib)
    store = rdfcore.SQLiteStore(tmp_path / 'terms.db') if persistent else None
    assert exercise(rdfcore, store) == expected
