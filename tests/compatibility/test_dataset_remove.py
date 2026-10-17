import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('kind', ['triple', 'all_graphs', 'named', 'default'])
@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_dataset_remove_scope(tmp_path, kind, union, backend):
    def observe(module, store=None):
        kwargs = {} if store is None else {'store': store}
        dataset = module.Dataset(default_union=union, **kwargs)
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        named = module.URIRef('urn:g')
        dataset.add(triple)
        dataset.add((*triple, named))
        pattern = {'triple': triple, 'all_graphs': (*triple, None),
                   'named': (*triple, named), 'default': (*triple, dataset.default_graph.identifier)}[kind]
        result = dataset.remove(pattern)
        remaining = sorted(tuple(str(term) for term in quad) for quad in dataset.quads())
        identity = result is dataset
        dataset.close()
        return identity, remaining
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore(tmp_path / 'remove.sqlite')
    assert observe(rdfcore, store) == observe(rdflib)
