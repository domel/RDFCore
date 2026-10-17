import pytest

from rdfcore import Graph, Literal, TripleTerm
from rdfcore.exceptions import ParserError


def test_compact_nested_triple_term_and_spaced_literal_suffix():
    graph = Graph().parse(data='<urn:s><urn:p><<(<urn:a><urn:b><<(<urn:c><urn:d>"x")>>)>> .', format='nt12')
    assert isinstance(next(iter(graph))[2], TripleTerm)
    graph = Graph().parse(data='<urn:s> <urn:p> "x" @en .', format='nt12')
    assert next(iter(graph))[2] == Literal('x', lang='en')


@pytest.mark.parametrize('literal', ['"x"@cantbethislong',
    '"x"^^<http://www.w3.org/1999/02/22-rdf-syntax-ns#langString>',
    '"x"^^<http://www.w3.org/1999/02/22-rdf-syntax-ns#dirLangString>'])
def test_rdf12_language_literals_require_wellformed_tag(literal):
    with pytest.raises(ParserError):
        Graph().parse(data=f'<urn:s> <urn:p> {literal} .', format='nt12')
