import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('kind', ['str', 'URIRef', 'BNode', 'Literal', 'Variable'])
def test_graph_identifier_and_resource_constructor(kind):
    def observe(module):
        value = 'urn:g' if kind == 'str' else getattr(module, kind)('urn:g')
        graph = module.Graph(identifier=value)
        resource = graph.resource(value)
        return type(graph.identifier).__name__, str(graph.identifier), type(resource.identifier).__name__, resource.identifier is value
    assert observe(rdfcore) == observe(rdflib)
