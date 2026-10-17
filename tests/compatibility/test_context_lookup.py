import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('identifier', ['existing', 'missing', 'string', 'none'])
@pytest.mark.parametrize('populated', [False, True])
def test_graph_lookup(identifier, populated):
    def observe(module):
        dataset = module.Dataset()
        graph = dataset.graph(module.URIRef('urn:g'))
        if populated:
            graph.add((module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')))
        key = {'existing': module.URIRef('urn:g'), 'missing': module.URIRef('urn:no'),
               'string': 'urn:g', 'none': None}[identifier]
        try:
            result = dataset.get_graph(key)
            return str(result.identifier), len(result)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


def test_context_views_keep_independent_base():
    def observe(module):
        dataset = module.Dataset()
        key = module.URIRef('urn:g')
        first = dataset.get_context(key, base='https://first/')
        second = dataset.get_context(key, base='https://second/')
        first.add((module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')))
        return first is second, first.base, second.base, len(second)
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('uri', ['https://example.org/doc#old', 'urn:document', '', None, 123])
@pytest.mark.parametrize('identifier', [None, '', '#new', 'child', 'https://other/x'])
def test_context_id_resolution(uri, identifier):
    def observe(module):
        try:
            result = module.Dataset().context_id(uri, identifier)
            return type(result).__name__, str(result)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('quoted', [False, True])
def test_context_views_share_store_and_namespaces(quoted):
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        key = module.URIRef('urn:g')
        first = dataset.get_context(key, quoted=quoted)
        second = dataset.get_context(key, quoted=quoted)
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        first.add(triple)
        assert triple in second
        assert first.store is dataset.store
        assert first.namespace_manager is dataset.namespace_manager
        second.remove(triple)
        assert triple not in first
