import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('name', ['URIRef', 'BNode', 'Variable'])
@pytest.mark.parametrize('value', ['', '?x', 'urn:x', 'żółć', "a'b"])
def test_term_conversions(name, value):
    def observe(module):
        try:
            term = getattr(module, name)(value)
            converted = term.toPython()
            return str(term), type(converted).__name__, converted, term.n3()
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)
