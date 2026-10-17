import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('missing', ['subject', 'predicate', 'object', 'two', 'none'])
@pytest.mark.parametrize('size', [0, 1, 2])
@pytest.mark.parametrize('unique', [False, True])
def test_value_matches_reference(missing, size, unique):
    def observe(module):
        graph = module.Graph()
        s, p, o = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')
        for index in range(size):
            graph.add((s, p, o if index == 0 else module.Literal('y')))
        kwargs = dict(subject=s, predicate=p, object=o, default='fallback', any=not unique)
        for key in ({'two': ['subject', 'object'], 'none': []}.get(missing, [missing])):
            kwargs[key] = None
        try:
            result = graph.value(**kwargs)
            if missing == 'object' and size == 2 and not unique:
                assert result in {module.Literal('x'), module.Literal('y')}
                return 'one of the matching objects'
            return type(result).__name__, str(result)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


def test_value_uses_default_predicate():
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        graph.add((module.URIRef('urn:s'), module.RDF.value, module.Literal('x')))
        assert graph.value(module.URIRef('urn:s')) == module.Literal('x')
