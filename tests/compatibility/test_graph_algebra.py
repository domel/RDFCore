"""Graph set operations compared with RDFLib's executable behavior."""
import operator

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('operation', [operator.add, operator.sub, operator.and_, operator.mul])
@pytest.mark.parametrize('kind', ['base', 'child', 'required'])
def test_graph_algebra_type_namespaces_and_terms(operation, kind):
    results = []
    for module in (rdflib, rdfcore):
        class Child(module.Graph):
            pass
        class Required(module.Graph):
            def __init__(self, identifier):
                super().__init__(identifier=identifier)
        left = (Child() if kind == 'child' else Required(module.URIRef('urn:left'))
                if kind == 'required' else module.Graph())
        right = module.Graph()
        left.bind('custom', module.Namespace('urn:a:'))
        right.bind('custom', module.Namespace('urn:b:'))
        common = (module.BNode('shared'), module.URIRef('urn:p'), module.Literal('same', lang='en'))
        left.add(common).add((module.URIRef('urn:left'), *common[1:]))
        right.add(common).add((module.URIRef('urn:right'), *common[1:]))
        result = operation(left, right)
        results.append((type(result).__name__,
                        sorted((p, str(ns)) for p, ns in result.namespaces()),
                        sorted(tuple((type(t).__name__, str(t), getattr(t, 'language', None))
                                     for t in row) for row in result), len(left), len(right)))
    assert results[0] == results[1]


def test_empty_graph_algebra_and_constructor_errors():
    for module in (rdflib, rdfcore):
        class Broken(module.Graph):
            def __init__(self, fail=False):
                if not fail:
                    raise RuntimeError('constructor error')
                super().__init__()
        for operation in (operator.add, operator.sub, operator.and_, operator.mul):
            assert len(operation(module.Graph(), module.Graph())) == 0
            with pytest.raises(RuntimeError, match='constructor error'):
                operation(Broken(True), module.Graph())
