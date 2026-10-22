"""Safe output: Turtle WD 2026-10-07 § 6.3; XML WD 2026-10-09 § 7.

Published documents and linked EDs checked 2026-10-22. No ED-only grammar.
"""
from xml.etree import ElementTree

import pytest

from rdfcore import Dataset, Graph, Literal, TripleTerm, URIRef
from rdfcore.compare import isomorphic


@pytest.mark.parametrize('format', ['turtle', 'trig', 'turtle12', 'trig12'])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
@pytest.mark.parametrize('base,suffix', [
    ('https://example.org/a', 'bc'), ('https://example.org/', 'urn:x'),
    ('https://example.org/', '..'), ('https://example.org/', '?q=x'),
    ('https://example.org/', 'name'), ('https://example.org/doc', ''),
])
def test_safe_iris_preserve_all_statement_positions(format, mode, base, suffix):
    iri = URIRef(base+suffix)
    value = Dataset() if format.startswith('trig') else Graph()
    triple = (iri, URIRef('urn:p'), iri)
    if isinstance(value, Dataset):
        value.graph(iri).add(triple)
    else:
        value.add(triple)
    options = {} if format.endswith('12') else {'safe_iris': True}
    output = value.serialize(format=format, mode=mode, base=base, **options)
    actual = (Dataset() if isinstance(value, Dataset) else Graph()).parse(data=output, format=format)
    assert isomorphic(value, actual)


@pytest.mark.parametrize('format', ['turtle12', 'trig12'])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
def test_safe_iris_apply_recursively_to_triple_terms(format, mode):
    iri = URIRef('https://example.org/a:inner')
    term = TripleTerm(iri, URIRef('urn:q'), TripleTerm(iri, URIRef('urn:q'), iri))
    value = Dataset() if format == 'trig12' else Graph()
    value.add((iri, URIRef('urn:p'), term))
    output = value.serialize(format=format, mode=mode, base='https://example.org/')
    actual = type(value)().parse(data=output, format=format)
    assert isomorphic(value, actual)


@pytest.mark.parametrize('format', ['xml', 'xml12'])
@pytest.mark.parametrize('predicate', ['http://www.w3.org/2000/xmlns/name',
                                       'http://www.w3.org/XML/1998/namespacelang'])
def test_safe_xml_namespace_output_is_valid_and_preserves_predicate(format, predicate):
    value = Graph().add((URIRef('urn:s'), URIRef(predicate), Literal('v')))
    options = {'safe_iris': True} if format == 'xml' else {}
    output = value.serialize(format=format, **options)
    ElementTree.fromstring(output)
    assert set(Graph().parse(data=output, format=format)) == set(value)


@pytest.mark.parametrize('format', ['xml12', 'turtle12', 'trig12', 'xml', 'turtle', 'trig'])
def test_safe_iris_requires_boolean(format):
    value = Dataset() if format.startswith('trig') else Graph()
    with pytest.raises(ValueError, match='safe_iris'):
        value.serialize(format=format, safe_iris='yes')
