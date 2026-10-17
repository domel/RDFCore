import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('operation', ['add', 'set', 'remove', 'predicates', 'value'])
@pytest.mark.parametrize('wrapped', [False, True])
def test_resource_keyword_arguments(operation, wrapped):
    def observe(module):
        graph = module.Graph()
        subject, predicate, obj = map(module.URIRef, ['urn:s', 'urn:p', 'urn:o'])
        graph.add((subject, predicate, obj))
        resource = graph.resource(subject)
        argument = graph.resource(obj) if wrapped else obj
        try:
            if operation == 'predicates':
                result = list(resource.predicates(o=argument))
                result = [str(item.identifier) for item in result]
            elif operation == 'value':
                result = resource.value(p=None, o=argument)
                result = str(result.identifier)
            else:
                result = getattr(resource, operation)(p=predicate, o=argument)
            return result, len(graph)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)
