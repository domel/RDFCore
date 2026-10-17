import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('left,right', [
    (('01', 'integer'), ('1', 'integer')),
    (('1', 'integer'), ('1.0', 'decimal')),
    (('x', None), ('x', 'string')),
    (('bad', 'integer'), ('other', 'integer')),
    (('x', 'unknown'), ('y', 'unknown')),
    (('x', 'unknown'), ('x', 'unknown')),
])
def test_literal_value_equality(left, right):
    def observe(module):
        def make(pair):
            lexical, local = pair
            datatype = None if local is None else module.URIRef('urn:unknown' if local == 'unknown' else str(module.XSD) + local)
            return module.Literal(lexical, datatype=datatype, normalize=False)
        a, b = make(left), make(right)
        try:
            return a.eq(b), a.neq(b)
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('value', ['x', 1, 1.0, True, None])
def test_literal_eq_python(value):
    def observe(module):
        return module.Literal('x').eq(value), module.Literal(1).eq(value)
    assert observe(rdfcore) == observe(rdflib)
