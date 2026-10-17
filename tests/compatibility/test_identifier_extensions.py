import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('value', ['a#', 'a#fragment', 'a', 'https://e/x#'])
def test_uri_base_fragment_and_concatenation(value):
    def observe(module):
        uri = module.URIRef(value, base='https://e/')
        return str(uri), uri.fragment, type(uri + 'x').__name__, type('prefix' + uri).__name__
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('kind', ['URIRef', 'BNode', 'Variable'])
def test_identifier_semantic_equality(kind):
    for module in (rdflib, rdfcore):
        term = getattr(module, kind)('x')
        assert term.eq(getattr(module, kind)('x')) is True
        assert term.neq('x') is True


def test_bnode_custom_identifier_generator():
    for module in (rdflib, rdfcore):
        assert str(module.BNode(_sn_gen=lambda: 'fixed', _prefix='B')) == 'Bfixed'
        generator = (value for value in ['first', 'second'])
        assert str(module.BNode(_sn_gen=generator, _prefix='B')) == 'Bfirst'


def test_invalid_uri_n3_raises():
    for module in (rdflib, rdfcore):
        with pytest.raises(Exception):
            module.URIRef('urn:bad iri').n3()
