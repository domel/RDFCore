import pytest
import rdflib
import rdfcore
from rdflib.collection import Collection as ReferenceCollection


@pytest.mark.parametrize('size', [0, 1, 3])
def test_clear_preserves_metadata_and_supports_reuse(size):
    def observe(module, collection_class):
        graph = module.Graph()
        head = module.URIRef('urn:list')
        collection = collection_class(graph, head, [module.Literal(str(i)) for i in range(size)])
        label = module.URIRef('urn:label')
        nodes = [head]
        node = head
        while (node := graph.value(node, module.RDF.rest)) is not None and node != module.RDF.nil:
            nodes.append(node)
        for node in nodes:
            graph.add((node, label, module.Literal('keep')))
        assert collection.clear() is collection
        assert collection.clear() is collection
        assert list(collection) == []
        assert len(graph) == len(nodes)
        assert all((node, label, module.Literal('keep')) in graph for node in nodes)
        collection.append(module.Literal('new'))
        return [str(item) for item in collection], len(graph)
    assert observe(rdfcore, rdfcore.Collection) == observe(rdflib, ReferenceCollection)
