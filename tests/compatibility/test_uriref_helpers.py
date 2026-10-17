import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('value', ['', 'urn:x', 'https://e/x#part', 'https://e/x#',
                                  'https://e/x?a=1#part', 'https://e/x%23part',
                                  'https://e/żółć#część'])
def test_uri_helpers_match_rdflib(value):
    def observe(module):
        uri = module.URIRef(value)
        plain = uri.toPython()
        result = uri.defrag()
        return type(plain).__name__, plain, type(result).__name__, str(result), result is uri
    assert observe(rdfcore) == observe(rdflib)
