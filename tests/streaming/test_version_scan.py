import pytest

from rdfcore import Literal, TripleTerm, URIRef, required_rdf_version


@pytest.mark.parametrize('dataset', [False, True])
def test_version_scan_stops_after_triple_term(dataset):
    s, p = URIRef('urn:s'), URIRef('urn:p')
    term = TripleTerm(s, p, Literal('x'))
    def statements():
        yield (s, p, term, URIRef('urn:g')) if dataset else (s, p, term)
        raise AssertionError('unnecessary read after RDF 1.2 was established')
    class Source:
        def __iter__(self):
            return statements()
    source = Source()
    if dataset:
        source.quads = statements
    assert required_rdf_version(source) == '1.2'


@pytest.mark.parametrize('objects,expected', [
    ([], '1.1'),
    ([Literal('plain')], '1.1'),
    ([Literal('x', lang='en', direction='ltr'), Literal('plain')], '1.2-basic'),
])
def test_lazy_version_scan_preserves_classification(objects, expected):
    statements = ((URIRef('urn:s'), URIRef('urn:p'), value) for value in objects)
    assert required_rdf_version(statements) == expected


def test_version_scan_does_not_stop_at_directional_literal():
    s, p = URIRef('urn:s'), URIRef('urn:p')
    def statements():
        yield s, p, Literal('x', lang='en', direction='rtl')
        yield s, p, TripleTerm(s, p, Literal('x'))
        raise AssertionError('unnecessary read after full RDF 1.2')
    assert required_rdf_version(statements()) == '1.2'
