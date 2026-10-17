import operator

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('left', ['URIRef', 'BNode', 'Variable'])
@pytest.mark.parametrize('right', ['URIRef', 'BNode', 'Variable'])
@pytest.mark.parametrize('operation', [operator.lt, operator.le, operator.gt, operator.ge])
def test_identifier_ordering(left, right, operation):
    def observe(module):
        return operation(getattr(module, left)('z'), getattr(module, right)('a'))
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('name', ['URIRef', 'BNode', 'Variable'])
def test_identifier_ordering_none(name):
    def observe(module):
        value = getattr(module, name)('x')
        return value < None, value > None, value <= None, value >= None
    assert observe(rdfcore) == observe(rdflib)
