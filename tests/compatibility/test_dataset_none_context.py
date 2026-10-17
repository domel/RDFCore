"""An explicit None quad context is not the same as a default-graph triple."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('default_union', [False, True])
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_explicit_none_context_matches_reference(default_union, backend, tmp_path):
    def scenario(module, store=None):
        dataset = module.Dataset(default_union=default_union, **({'store': store} if store is not None else {}))
        triple = tuple(map(module.URIRef, ('urn:s', 'urn:p', 'urn:o')))
        assert dataset.add((*triple, None)) is dataset
        assert dataset.add((*triple, None)) is dataset
        observed = (len(dataset), len(dataset.default_graph), len(list(dataset.quads())),
                    len(list(dataset.triples((None, None, None)))))
        return observed
    expected = scenario(rdflib)
    store = rdfcore.SQLiteStore(tmp_path / 'none.sqlite') if backend == 'sqlite' else rdfcore.Memory()
    try:
        assert scenario(rdfcore, store) == expected
        if backend == 'sqlite':
            store.close()
            store = rdfcore.SQLiteStore(tmp_path / 'none.sqlite')
            assert scenario(rdfcore, store) == expected
    finally:
        store.close()
