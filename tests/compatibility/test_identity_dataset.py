import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('left', ['URIRef', 'BNode', 'Variable', 'Literal'])
@pytest.mark.parametrize('right', ['URIRef', 'BNode', 'Variable', 'Literal'])
def test_term_identity(left, right):
    def observe(module):
        a = getattr(module, left)('urn:x')
        b = getattr(module, right)('urn:x')
        return a == b, a != b, len({a, b}), a == 'urn:x'
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('named', [False, True])
def test_dataset_iteration_and_length(union, named):
    def observe(module):
        dataset = module.Dataset(default_union=union)
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        dataset.add(triple)
        if named:
            dataset.graph(module.URIRef('urn:g')).add(triple)
        return len(dataset), sorted(tuple(str(t) for t in q) for q in dataset), len(dataset.default_graph)
    assert observe(rdfcore) == observe(rdflib)


def test_empty_dataset():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        assert len(dataset) == 0
        assert list(dataset) == []
        assert len(dataset.default_graph) == 0
