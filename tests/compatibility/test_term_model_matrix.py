"""Executable term ordering/identity matrix against RDFLib 7.6.0."""
import operator
from functools import lru_cache

import pytest
import rdflib
import rdfcore


KINDS = ['uri', 'uri-subclass', 'bnode', 'bnode-subclass', 'variable',
         'literal', 'literal-subclass', 'language', 'integer', 'lexical-integer',
         'nan', 'infinity', 'date', 'aware-datetime', 'str', 'none', 'foreign']


@lru_cache(maxsize=None)
def subclass(module, name):
    parent = {'uri': module.URIRef, 'bnode': module.BNode, 'literal': module.Literal}[name]
    return type('TermSubclass', (parent,), {})


def term(module, kind):
    if kind == 'none': return None
    if kind == 'foreign': return object()
    if kind == 'str': return 'x'
    if kind == 'uri': return module.URIRef('x')
    if kind == 'bnode': return module.BNode('x')
    if kind == 'variable': return module.Variable('x')
    if kind.endswith('-subclass'):
        return subclass(module, kind[:-9])('x')
    if kind == 'literal': return module.Literal('x')
    if kind == 'language': return module.Literal('x', lang='EN')
    if kind == 'integer': return module.Literal(1)
    if kind == 'lexical-integer': return module.Literal('01', datatype=module.XSD.integer, normalize=False)
    if kind == 'nan': return module.Literal('NaN', datatype=module.XSD.double)
    if kind == 'infinity': return module.Literal('INF', datatype=module.XSD.double)
    if kind == 'date': return module.Literal('2020-02-29', datatype=module.XSD.date)
    if kind == 'aware-datetime': return module.Literal('2020-02-29T12:00:00+02:00', datatype=module.XSD.dateTime)
    raise AssertionError(kind)


@pytest.mark.parametrize('left', KINDS)
@pytest.mark.parametrize('right', KINDS)
@pytest.mark.parametrize('operation', [operator.eq, operator.ne, operator.lt,
                                       operator.le, operator.gt, operator.ge])
def test_term_comparison_matrix(left, right, operation):
    def observe(module):
        try:
            result = operation(term(module, left), term(module, right))
            return type(result).__name__, result
        except Exception as exc:
            return type(exc).__name__, None
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('left', KINDS[:-1])
@pytest.mark.parametrize('right', KINDS[:-1])
def test_term_set_and_dictionary_matrix(left, right):
    def observe(module):
        a, b = term(module, left), term(module, right)
        original = hash(a)
        return (len({a, b}), b in {a}, {a: 'value'}.get(b),
                original == hash(a), (a == b) == (b == a))
    assert observe(rdfcore) == observe(rdflib)
