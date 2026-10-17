import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('same_identifier', [False, True])
@pytest.mark.parametrize('same_store', [False, True])
def test_graph_and_resource_identity(same_identifier, same_store):
    def observe(module):
        first = module.Graph(identifier=module.URIRef('urn:g'))
        second = module.Graph(identifier=module.URIRef('urn:g' if same_identifier else 'urn:h'),
                              **({'store': first.store} if same_store else {}))
        a = first.resource(module.URIRef('urn:s'))
        b = second.resource(module.URIRef('urn:s'))
        return (first == second, first != second, len({first, second}),
                a == b, a != b, len({a, b}), first == 'urn:g')
    assert observe(rdfcore) == observe(rdflib)
